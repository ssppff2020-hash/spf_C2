#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
C2 论文 · 第 0 步：TeX Live 环境准备（可复跑）

为什么需要这个脚本
------------------
本机安装 TeX Live 2026 时，官方 installer 的 `tar.exe` 在解包阶段对本机临时目录
反复报 `Permission denied`（root cause 未定，疑似安全软件对新建归档的实时扫描），
导致 30 个包被跳过、`kpsewhich.exe` 等核心可执行文件缺失、`pdflatex.fmt` 无法生成。

补救办法就是本脚本：直接用 Python 下载 + 系统 tar 解包，把 TeX Live 的
**包（.tar.xz）** 当作纯数据文件处理，绕开 installer 的打包/解包链路。

这也让"环境如何搭起来"变成了可复现的代码，而不是一段口述经验。

用法
----
  # 装缺失的包
  python 00_setup_texlive.py install dehyph-exptl hyphen-german

  # 只重建文件名数据库与 pdflatex 格式
  python 00_setup_texlive.py refresh

  # 查看当前状态
  python 00_setup_texlive.py doctor

环境变量
--------
  TEXLIVE_ROOT   TeX Live 安装根目录（默认 C:/Users/<user>/texlive/2026）
  TLNET_MIRROR   镜像地址（默认腾讯云 CTAN 镜像）
"""

from __future__ import annotations

import os
import tarfile
import shutil
import subprocess
import sys
from pathlib import Path

import requests

DEFAULT_ROOT = Path(os.environ.get("TEXLIVE_ROOT",
                                   str(Path.home() / "texlive" / "2026")))
MIRROR = os.environ.get(
    "TLNET_MIRROR",
    "https://mirrors.cloud.tencent.com/CTAN/systems/texlive/tlnet")
CACHE = Path(os.environ.get("TEMP", "/tmp")) / "c2_tl_cache"
BIN = DEFAULT_ROOT / "bin" / "windows"


def log(msg: str) -> None:
    print(f"[tl] {msg}", flush=True)


def fetch_package(name: str) -> Path:
    """下载 archive/<name>.tar.xz 到本地缓存。"""
    CACHE.mkdir(parents=True, exist_ok=True)
    dest = CACHE / f"{name}.tar.xz"
    if dest.exists() and dest.stat().st_size > 0:
        log(f"{name}: 命中缓存 ({dest.stat().st_size} B)")
        return dest
    url = f"{MIRROR}/archive/{name}.tar.xz"
    log(f"{name}: GET {url}")
    with requests.get(url, stream=True, timeout=600) as r:
        if r.status_code != 200:
            raise RuntimeError(f"{name}: HTTP {r.status_code}")
        with open(dest, "wb") as f:
            for chunk in r.iter_content(1 << 16):
                f.write(chunk)
    log(f"{name}: 下载完成 ({dest.stat().st_size} B)")
    return dest


# 归档顶层目录 → 解包目标（相对 TeX Live 根）。
# TeX Live 的包归档**不是**统一相对根的：内容包相对 texmf-dist，
# 二进制包相对根。搞错这一层，文件就会落在 kpathsea 看不见的地方。
TEXMFDIST_DIRS = {"tex", "fonts", "doc", "bibtex", "scripts", "metapost",
                  "web2c", "makeindex", "source", "context", "asymptote"}


def extract(archive: Path, override: str | None = None) -> str:
    """用 Python 标准库 tarfile 解包，**不调用系统 tar**。

    为什么不用系统 tar：本机 PATH 上同时存在 Windows 自带的 bsdtar
    （C:\\Windows\\System32\\tar.exe）和 MSYS 的 GNU tar。二者对路径的
    理解完全不同 —— bsdtar 不认 `/c/...`，GNU tar 又把 `C:` 当远端主机名。
    Python 的 tarfile 两边的坑都不踩，而且能正确处理归档里的符号链接。
    """
    with tarfile.open(archive, "r:xz") as tf:
        tops = {m.name.split("/")[0] for m in tf.getmembers() if m.name.strip()}

        if override:
            where = override
        elif tops & TEXMFDIST_DIRS:
            where = "texmf-dist"
        else:
            where = "."

        target = DEFAULT_ROOT / where if where != "." else DEFAULT_ROOT
        target.mkdir(parents=True, exist_ok=True)

        # filter="data" 会拒绝绝对路径与 ../ 逃逸，是 Python 3.12+ 的推荐做法；
        # 3.11 尚无该参数，故按版本兼容处理。
        try:
            tf.extractall(target, filter="data")     # noqa: S202
        except TypeError:
            tf.extractall(target)                    # noqa: S202
    return where


def fix_language_dat() -> None:
    """把 language.dat 裁剪成「只引用本机确实装了的断词模式」。

    背景：`texmf-dist` 里自带的 language.dat 是**出厂全量版**，列了 60 多种语言。
    正常情况下 tlmgr 会在安装后按实际安装的包重新生成它；本机的 tlmgr 没能跑起来，
    于是 pdflatex 格式在构建时就卡在 `I can't find file 'loadhyph-af.tex'` ——
    一个语言一个语言地报错，属于典型的"打地鼠"。

    做法：逐行解析，用 kpsewhich 判断该行引用的模式文件在不在；
    不在的整行注释掉（保留原文，便于对照），结果写入 texmf-config。
    kpathsea 的搜索顺序里 texmf-config 排在 texmf-dist 之前，因此会优先生效。
    """
    src = DEFAULT_ROOT / "texmf-dist" / "tex" / "generic" / "config" / "language.dat"
    if not src.exists():
        log("找不到 language.dat，跳过裁剪")
        return
    kpse = BIN / "kpsewhich.exe"
    if not kpse.exists():
        log("kpsewhich.exe 缺失，跳过裁剪")
        return

    def exists(fname: str) -> bool:
        r = subprocess.run([str(kpse), fname], capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() != ""

    kept, dropped = [], []
    for raw in src.read_text(encoding="latin-1").splitlines():
        line = raw.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("%") or stripped.startswith("="):
            kept.append(line)
            continue
        parts = stripped.split()
        # 语法：<语言名> <模式文件> [<例外文件>]
        files = [p for p in parts[1:] if p.endswith(".tex")]
        if files and all(exists(f) for f in files):
            kept.append(line)
        else:
            dropped.append(stripped)
            kept.append(f"% [C2] disabled (pattern not installed): {stripped}")

    dst_dir = DEFAULT_ROOT / "texmf-config" / "tex" / "generic" / "config"
    dst_dir.mkdir(parents=True, exist_ok=True)
    # 注意：language.dat 是 latin-1 编码的老式 TeX 配置，注释只能用 ASCII，
    # 否则 write_text 会抛 UnicodeEncodeError（本机踩过）。
    header = (
        "% [C2] Generated by pipeline/00_setup_texlive.py::fix_language_dat().\n"
        "% Source: texmf-dist/tex/generic/config/language.dat (full factory list).\n"
        f"% Enabled {len(kept) - len(dropped)} lines; "
        f"disabled {len(dropped)} uninstalled language patterns.\n"
    )
    (dst_dir / "language.dat").write_text(header + "\n".join(kept) + "\n",
                                          encoding="latin-1")
    log(f"language.dat 已裁剪：禁用 {len(dropped)} 种未安装语言的断词模式")


def patch_scripts() -> None:
    """修 TeX Live 自带 Perl 脚本在 Windows 上的 PATH 分隔符 bug。

    `updmap.pl` / `fmtutil.pl` / `tlmgr.pl` 都用

        $ENV{"PATH"} = "$bindir:$ENV{PATH}";

    把 bin 目录拼到 PATH 前面 —— 分隔符写死成 Unix 的 `:`。
    在 Windows 上 PATH 用 `;`，于是这行会产出

        C:/.../bin/windows:C:\\Users\\...\\texlive\\2026\\bin\\windows;C:\\...

    cmd.exe 把前两段当成**一个**畸形项，真正含 kpsewhich 的那一段就被吞掉了，
    脚本随即以 `kpsewhich ... failed` 中止。表现是"脚本静默失败或立刻退出"。

    这属于 TeX Live 自身在 MSYS/Windows 混合环境下的缺陷，与我们的挑战无关，
    但会让 tlmgr / updmap 完全不可用，所以在此就地修正（原行保留为注释）。
    """
    fixed = 0
    for name in ["updmap.pl", "fmtutil.pl", "tlmgr.pl"]:
        p = DEFAULT_ROOT / "texmf-dist" / "scripts" / "texlive" / name
        if not p.exists():
            continue
        s = p.read_text(encoding="utf-8", errors="surrogateescape")
        old = '$ENV{"PATH"} = "$bindir:$ENV{PATH}";'
        new = ('# [C2 PATCH] Windows PATH separator is ";" not ":" '
               '(original line kept below as a comment)\n'
               '  $ENV{"PATH"} = "$bindir" . ($^O eq "MSWin32" ? ";" : ":") '
               '. $ENV{PATH};')
        if old in s:
            p.write_text(s.replace(old, new), encoding="utf-8",
                         errors="surrogateescape")
            fixed += 1
    log(f"已修正 {fixed} 个 TeX Live 脚本的 PATH 分隔符问题")


def run_updmap() -> None:
    """生成 pdftex.map —— 没有它，pdfTeX 找不到任何 .pfb 字体。

    直接调 updmap.pl（配 tlperl），绕过同样坏掉的 updmap-sys 包装器。
    先 `--syncwithtrees` 摘掉指向未安装包的 map 条目，再正常跑一遍；
    syncwithtrees 会交互式提问，这里用 'y\\n' 应答。
    """
    perl = DEFAULT_ROOT / "tlpkg" / "tlperl" / "bin" / "perl.exe"
    script = DEFAULT_ROOT / "texmf-dist" / "scripts" / "texlive" / "updmap.pl"
    if not perl.exists() or not script.exists():
        log("updmap 前置条件缺失，跳过")
        return
    env = dict(os.environ)
    env["PATH"] = str(BIN) + os.pathsep + env.get("PATH", "")
    subprocess.run([str(perl), str(script), "--sys", "--syncwithtrees"],
                   input="y\n", capture_output=True, text=True, env=env)
    r = subprocess.run([str(perl), str(script), "--sys"],
                       capture_output=True, text=True, env=env)
    target = DEFAULT_ROOT / "texmf-var" / "fonts" / "map" / "pdftex" / "updmap" / "pdftex.map"
    log(f"pdftex.map {'已生成' if target.exists() else '未生成'}"
        f"（updmap 退出码 {r.returncode}）")


def mktexlsr() -> None:
    exe = BIN / "mktexlsr.exe"
    if not exe.exists():
        log("mktexlsr.exe 缺失，跳过（kpathsea 会退化为目录扫描）")
        return
    subprocess.run([str(exe)], capture_output=True, text=True)
    log("文件名数据库 ls-R 已更新")


def make_fmt() -> None:
    """直接调用 pdftex -ini 生成 pdflatex.fmt。

    注意顺序：**生成 .fmt 之后必须再跑一次 mktexlsr**。
    texmf-var 下一旦存在 ls-R，kpathsea 就会只信 ls-R 而不再扫描目录，
    新生成的 pdflatex.fmt 没有进索引就等于不存在（本机踩过这个坑）。

    不走 `fmtutil-sys`：本机的 fmtutil 包装器（runscript.exe + runscript.dll）
    版本错配，静默返回 0 却不产出任何东西。直接调引擎更可靠，也更容易排查。
    """
    outdir = DEFAULT_ROOT / "texmf-var" / "web2c" / "pdftex"
    outdir.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env["PATH"] = str(BIN) + os.pathsep + env.get("PATH", "")
    cmd = [str(BIN / "pdftex.exe"), "-ini", "-interaction=nonstopmode",
           "-jobname=pdflatex", "-progname=pdflatex",
           "-translate-file=cp227.tcx", "*pdflatex.ini"]
    r = subprocess.run(cmd, cwd=str(outdir), env=env,
                       capture_output=True, text=True)
    fmt = outdir / "pdflatex.fmt"
    log(f"pdftex -ini 退出码 {r.returncode}；pdflatex.fmt {'已生成' if fmt.exists() else '未生成'}")
    if not fmt.exists():
        tail = (r.stdout or "")[-1500:]
        print(tail)
        raise SystemExit(1)


def doctor() -> None:
    log(f"TEXLIVE_ROOT = {DEFAULT_ROOT}")
    log(f"存在        = {DEFAULT_ROOT.exists()}")
    for exe in ["pdftex.exe", "pdflatex.exe", "kpsewhich.exe", "bibtex.exe",
                "mktexlsr.exe"]:
        log(f"  {exe:<16} {'OK' if (BIN/exe).exists() else '缺失'}")
    fmt = DEFAULT_ROOT / "texmf-var" / "web2c" / "pdftex" / "pdflatex.fmt"
    log(f"  pdflatex.fmt     {'OK' if fmt.exists() else '缺失'}")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("install", "refresh", "doctor",
                                                "patch"):
        print(__doc__)
        return 2
    action = sys.argv[1]

    if action == "doctor":
        doctor()
        return 0

    if action == "patch":
        patch_scripts()
        return 0

    if action == "install":
        for name in sys.argv[2:]:
            try:
                where = extract(fetch_package(name))
                log(f"{name}: 已解包 → {where}")
            except Exception as e:                      # noqa: BLE001
                log(f"{name}: 失败 -> {e}")
        fix_language_dat()
        mktexlsr()
        make_fmt()
        mktexlsr()          # 见 make_fmt 注释：新格式必须重新入库
        run_updmap()
        return 0

    if action == "refresh":
        patch_scripts()
        fix_language_dat()
        mktexlsr()
        make_fmt()
        mktexlsr()          # 见 make_fmt 注释：新格式必须重新入库
        run_updmap()
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
