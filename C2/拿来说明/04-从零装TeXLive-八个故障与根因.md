# 拿来说明 04 · 从零装 TeX Live：八个故障与根因

> **一句话**：本机没有任何 TeX 发行版，而「不可编译」是红线（≤ 5 分）。
> 装的过程中撞上 8 个独立故障，**全部定位到根因，没有一次用「重装试试」**。
> 对策已全部固化成 [`pipeline/00_setup_texlive.py`](../pipeline/00_setup_texlive.py)。

---

## 一、起点：先验证能不能，再决定怎么做

```
$ which pdflatex xelatex latexmk tectonic
which: no pdflatex in (...)
```

**不写「环境限制」直接放弃。** 先做可达性探测（C1 教训：「做不到」之前先换条路径验证）：

```
arxiv.org                       : 200
github.com                      : 200
ctan.org                        : 000     ← 不通
mirrors.cloud.tencent.com/CTAN/ : 200     1.48 MB/s   ← 最快
mirrors.ustc.edu.cn/CTAN/       : 200     1.21 MB/s
```

**结论：网络是通的，只是 `ctan.org` 这个域名不通。**
换腾讯云镜像，速度足够装完整套 TeX Live。

---

## 二、八个故障

### 故障 1 · installer 的 Perl 缺模块

```
Can't locate Pod/Usage.pm in @INC (...) at ./install-tl line 147.
```

MSYS 自带 Perl 缺 `Pod::Usage`。

**不去补 CPAN 模块**。TeX Live 的 Windows 安装包里**自带了完整 Perl**：

```bash
./tlpkg/tlperl/bin/perl.exe ./install-tl -profile ./tl.profile -repository ...
```

> **教训**：装一个东西之前，先看它自带了什么。

### 故障 2 · 解包 Permission denied（30 个包）

```
Installing [6/6]: tlperl.windows [7296k]
tar: Cannot open C:\...\pAfIwk9b55/tlperl.windows.tar: Permission denied
```

**关键判断**：手工下一份验证——`curl` + `tar -xf` **成功**，排除「包坏了」。
于是重跑 installer。

**第二次，同样的错误，但换到了 `adobemapping`。**

> **报错换了包 ⇒ 不是这个包的问题，是解包链路的问题。**
> 这个判断避免了在单包上浪费时间。后面陆续 30 个包栽在同一模式上。

根因未最终确定（最可能是安全软件对 installer 新建归档做实时扫描、短暂占用）。
**不硬刚，换路**：绕开 installer 的解包链路，把包当纯数据文件，自己下、自己解。

### 故障 3 · MSYS tar 把 `C:` 当远端主机名

```
tar: Cannot connect to C: resolve failed
```

GNU tar 把 `C:/...` 解释成「主机 C 上的路径」。用 `/c/...` 形式可解——
**但这只在从 bash 手动跑的时候成立**。

### 故障 4 · Python 调到的其实是**另一个** tar

同一个文件，bash 里 `tar -tf` 能开，Python 的 `subprocess` 开不了：

```
tar: Error opening archive: Failed to open
'/c/Users/spf_2/AppData/Local/Temp/c2_tl_cache/dehyph-exptl.tar.xz'
```

**根因**：PATH 上有两个 tar，且它们对路径的理解**正好相反**：

| | 程序 | 不认什么 |
|---|---|---|
| `C:\Windows\System32\tar.exe`（bsdtar，Windows 自带） | Python 的 `subprocess` 解析到这个 | 不认 `/c/...` |
| `/usr/bin/tar`（GNU tar，MSYS） | bash 解析到这个 | 把 `C:\` 当主机名 |

**最终修法：彻底不调外部 tar，改用 Python 标准库 `tarfile`。**

```python
with tarfile.open(archive, "r:xz") as tf:
    ...
```

> **教训**：跨 bash / Python / Windows 三层的时候，**外部命令的解析结果可能不一致**。
> 能用标准库解决的，就不要经过 shell。

### 故障 5 · 解包目标搞错了（不报错，只是找不到）

**TeX Live 的包归档不是统一相对根的。**

| 归档 | 内部顶层目录 | 解包目标 |
|---|---|---|
| `texlive.infra.windows` | `bin/windows/...` | 安装根 |
| `lm` / `amsfonts` / `dehyph-exptl` | `tex/generic/...`、`fonts/...` | **`texmf-dist/`** |

解错一层，文件落在 kpathsea 看不见的地方，**不报错，只是找不到**。

**修法**：扫描归档顶层目录，落在 `{tex, fonts, doc, bibtex, scripts, metapost, ...}`
里的解到 `texmf-dist/`，其余解到根。

### 故障 6 · 格式构建的「打地鼠」（66 种语言）

```
! I can't find file `dehypht-x-2024-02-28.tex'.
! I can't find file `loadhyph-af.tex'.
! I can't find file `loadhyph-sq.tex'.
...
```

**根因**：`texmf-dist` 自带的 `language.dat` 是**出厂全量版**，列了 66 种语言。
正常由 `tlmgr` 在安装后按实际装的包重新生成；本机 tlmgr 没跑起来，
于是 pdflatex 构建格式时挨个去 `\input` 那些没装的模式文件。

**修法不是去装那 66 个包**（那是打地鼠），而是**按实际存在的文件裁剪配置**：

```python
for raw in language.dat:
    parts = raw.split()
    files = [p for p in parts[1:] if p.endswith(".tex")]
    if files and all(exists(f) for f in files):
        kept.append(line)          # 模式文件在 → 保留
    else:
        kept.append(f"% [C2] disabled (pattern not installed): {line}")
```

写到 `texmf-config/`（kpathsea 搜索顺序里排在 `texmf-dist` 之前），一次成功。

> **教训**：当报错一个接一个出现且模式相同时，**缺的不是补丁，是对机制的理解**。
> 读明白 `language.dat` 在干什么之后，修法是「裁剪它」而不是「满足它」。

### 故障 7 · PATH 分隔符 —— TeX Live 自己的 bug

```
'kpsewhich' 不是内部或外部命令
updmap.pl: kpsewhich -var-value=TEXMFROOT failed, aborting early.
updmap.pl:   had PATH: C:/.../bin/windows:C:\Users\spf_2\texlive\2026\bin\windows;...
```

**看分隔符**：第一个是 `:`，后面全是 `;`。

源码（`updmap.pl:37`、`fmtutil.pl:32`、`tlmgr.pl:63` 三处一样）：

```perl
$ENV{"PATH"} = "$bindir:$ENV{PATH}";      # 分隔符写死成 Unix 的 ":"
```

Windows 上 cmd.exe 把 `C:/.../bin/windows:C:\Users\...\bin\windows`
当成**一个**畸形项，真正含 kpsewhich 的那一段被吞掉。

**修法**（三处都改）：

```perl
$ENV{"PATH"} = "$bindir" . ($^O eq "MSWin32" ? ";" : ":") . $ENV{PATH};
```

修完 `updmap` 立刻能跑。这属于修改第三方工具，所以在脚本里注明了原因，
并把原行保留为注释。

### 故障 8 · 字体映射缺失 + 一个顺序坑

```
!pdfTeX error: pdflatex.exe (file ec-lmbx10): Font ec-lmbx10 at 657 not found
```

根因：`pdftex.map` 没生成，pdfTeX 找不到任何 `.pfb`。

`updmap` 先卡在未安装包的 map 条目上：

```
updmap [ERROR]: zi4.map (in .../updmap.cfg)
updmap [ERROR]: Did you run mktexlsr?
```

用 `--syncwithtrees` 摘掉——但**它会交互式提问**，第一遍回了 `n`，
于是什么都没改。回 `y` 之后生成成功。

**隐蔽的顺序坑**：`texmf-var` 下一旦有 `ls-R`，kpathsea 就**只信 `ls-R` 不再扫目录**。
新生成的 `pdflatex.fmt` 没进索引就等于不存在。

> **所以必须在生成 `.fmt` 之后再跑一次 `mktexlsr`。**

---

## 三、最终验收

```
[tl] TEXLIVE_ROOT = C:\Users\spf_2\texlive\2026
[tl]   pdftex.exe       OK
[tl]   pdflatex.exe     OK
[tl]   kpsewhich.exe    OK
[tl]   bibtex.exe       OK
[tl]   mktexlsr.exe     OK
[tl]   pdflatex.fmt     OK
```

论文编译通过：

```
[build] pdflatex#1=0 bibtex=0 pdflatex#3=0
[build] paper.pdf: 15 pages, 455613 bytes
[build] OK -- no undefined references, citations or control sequences.
```

---

## 四、八个故障分类

| 类别 | 故障 | 本质 |
|---|---|---|
| 前置条件 | 1（Perl 模块） | 没先看工具有没有自带 |
| **环境行为** | 2（Permission denied） | installer 的解包链路在本机不可用 |
| **跨层不一致** | **3 + 4（两个 tar）** | bash / Python / Windows 三层对外部命令的解析不一致 |
| 正确性 | 5（解包目标） | 归档布局不是统一的 |
| **机制理解** | **6（language.dat）** | 打地鼠 vs 理解配置机制 |
| 第三方缺陷 | 7（PATH 分隔符） | TeX Live 脚本在 MSYS/Windows 下的真 bug |
| 顺序 | 8（ls-R 索引） | 索引先于产物生成，产物就等于不存在 |

---

## 五、带走的三条

1. **报错换了对象，就说明不是那个对象的问题。**
   故障 2 从 `tlperl` 换到 `adobemapping`，这一条信号立刻把排查方向从
   「这个包怎么了」转到「解包链路怎么了」。

2. **当报错同模式地反复出现，停下来读机制，不要继续打补丁。**
   故障 6 如果去装 66 个包，能装完，但下次换个环境还会再遇到。
   读明白 `language.dat` 之后，修法是 6 行代码。

3. **环境搭建也要脚本化。**
   8 个故障的对策现在都在 `pipeline/00_setup_texlive.py` 里，
   换一台机器跑一遍 `python 00_setup_texlive.py refresh` 即可。
   **一段口述的「我是这么装的」不是可复现性。**

---

## 六、事后看，可以更快的两个地方

- **故障 2 → 4 之间绕了两圈**：先怀疑路径格式，再怀疑 tar 版本，
  最后才想到「绕开整个解包链路」。
  正确的判断顺序应该是：**先问「主流程本身是不是坏的」，再问「主流程里哪一步坏了」。**
- **故障 6 的第一反应是「把缺的包都装上」**。那是打地鼠。
  真正的省时动作是**先去读那个配置文件在干什么**。
