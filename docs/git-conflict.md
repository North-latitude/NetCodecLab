# Git 合并冲突演练记录

> 对应组内交接表里的「冲突演练」环节与作业要求「制造并解决冲突」。
> 本文件记录的是**真实发生的冲突**，不是编造的示例：两个分支改了同一行，
> GitHub 上 PR #8 一度显示 `mergeable = false`，本地 `git merge` 产出冲突标记后才解开。

| 项目 | 内容 |
| :--- | :--- |
| 时间 | 2026-11-08 |
| 参与 | 高郑豪（组长）、周恩旭 |
| 冲突文件 | `app/common/config.py` |
| 冲突行 | 第 13 行 `DEFAULT_ENCODING` |
| 分支 | `feature/conflict-a`（PR #7）与 `feature/conflict-b`（PR #8） |
| 合并顺序 | 先合 #7，再合 #8 → 触发冲突 |

> 说明：分支名里的 `a` / `b` 只是 Git 分支标识，**不对应任何人员编号**；参与者就是高郑豪与周恩旭两人。

---

## 1. 冲突是怎么来的

两位同学都要改**默认字符集**这一个常量，理由都很正当：

- **周恩旭（PR #7）**：GBK 编不了 emoji，默认应该用 UTF-8，
  ```python
  DEFAULT_ENCODING = "utf-8"  # 统一 UTF-8，GBK 编不了 emoji
  ```
- **高郑豪（PR #8）**：中文演示时 GBK 每个汉字只要 2 字节，更能体现编码差异，
  ```python
  DEFAULT_ENCODING = "gbk"  # 中文演示优先，两字节更省
  ```

两条改动落在**同一个文件的同一行**上，Git 无法自动判断该留哪一条。

## 2. 冲突现场

`feature/conflict-a` 先合并进 `main`，然后在 `feature/conflict-b` 上拉取最新代码：

```text
$ git checkout feature/conflict-b
$ git fetch origin
$ git merge origin/main

Auto-merging app/common/config.py
CONFLICT (content): Merge conflict in app/common/config.py
Automatic merge failed; fix conflicts and then commit the result.
```

`git status` 显示这个文件处于未合并状态：

```text
Unmerged paths:
  (use "git add <file>..." to mark resolution)
	both modified:   app/common/config.py
```

打开文件，看到 Git 写进去的三段标记：

```python
# 默认字符集：编码工坊与纠错演示都以 UTF-8 为准，GBK 作为对比项
<<<<<<< HEAD
DEFAULT_ENCODING = "gbk"  # 中文演示优先，两字节更省
=======
DEFAULT_ENCODING = "utf-8"  # 统一 UTF-8，GBK 编不了 emoji
>>>>>>> origin/main
```

含义：

| 标记 | 指的是 |
| :--- | :--- |
| `<<<<<<< HEAD` 到 `=======` | **当前分支**（`feature/conflict-b`）的版本，即 GBK |
| `=======` 到 `>>>>>>> origin/main` | **要合进来的** `main` 的版本，即 UTF-8 |

## 3. 怎么解决的

两人在群里对了一遍，结论是**保留 UTF-8**，理由不是「谁的先合谁赢」，而是能不能跑：

1. GBK 只覆盖中日韩常用字符集，遇到 emoji 直接抛 `UnicodeEncodeError`；
2. 如果默认值用 GBK，编码工坊一打开就会整页解析失败，演示直接翻车；
3. GBK 的价值在于「对比 2 字节 vs 3 字节」，这个通过**字符集下拉框手动切换**同样能看到，不必改默认值。

于是删掉三段标记，只留下正确的那一行，并把这个结论写进注释，避免下次又有人踩：

```python
# 默认字符集：统一用 UTF-8。
# 冲突演练结论（见 docs/git-conflict.md）：GBK 编不了 emoji，会让整个页面解析失败，
# 所以默认值保留 UTF-8；GBK 仍可通过编码工坊的字符集下拉框手动切换做对比演示。
DEFAULT_ENCODING = "utf-8"
```

然后按标准动作提交：

```text
$ git add app/common/config.py
$ git commit -m "merge: 解决 DEFAULT_ENCODING 合并冲突"
$ git push origin feature/conflict-b
```

## 4. 解决后的验证

| 检查项 | 结果 |
| :--- | :--- |
| `git status` 不再有 `Unmerged paths` | ✅ |
| 文件里搜不到 `<<<<<<<` / `=======` / `>>>>>>>` | ✅ `grep` 结果为空 |
| GitHub 上 PR #8 从 `mergeable=false` 变为可合并 | ✅ |
| 合并后 `python -m unittest discover -s tests` | ✅ 76 个用例通过 |
| 合并后 `python tools/verify_core.py` | ✅ 13 项验收通过 |

## 5. 复盘：这次学到了什么

1. **冲突不可怕，可怕的是"随便挑一个"**。冲突的两边通常都是对的，只是场景不同；
   必须回到「谁来用、什么时候用」来判断，而不是看谁的分支先合。
2. **冲突经常出现在"配置常量"这种小地方**，而不是大家以为的算法文件——
   因为每个人都会顺手改一下默认值。
3. **把结论写回代码注释**。这次把决议写进了 `config.py` 的注释里，
   下次再有人想改默认字符集，会先看到"为什么是 UTF-8"。
4. **冲突标记必须清干净**。`<<<<<<<` 留在代码里不会报错（Python 里 `<<` 是左移运算符），
   但程序必然跑不对，属于最隐蔽的一类事故。

## 6. 常用命令速查

```bash
git status                 # 看哪些文件冲突了
git diff                   # 看冲突块的具体差异
git checkout --ours  file  # 全用当前分支的版本（会丢掉对方的改动，慎用）
git checkout --theirs file # 全用对方分支的版本（同样慎用）
git add file               # 手工解决完后标记为已解决
git commit                 # 完成合并提交
git merge --abort          # 反悔，回到合并前
```
