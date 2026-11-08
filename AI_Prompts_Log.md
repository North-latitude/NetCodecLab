# AI_Prompts_Log —— AI 结对编程记录

> 记录格式：每位成员 3 条，共 12 条；每条分 **提示词 / AI 输出 / 人工修改 / 反思** 四段。
> 这里只收“**AI 出错、人工抓出来**”的真实案例——照着抄就能跑的那种不写。

| 编号 | 成员 | 模块 | 一句话 |
| :--- | :--- | :--- | :--- |
| 01 | 高郑豪 | 奇偶校验 | AI 只实现了偶校验，`odd` 分支是摆设 |
| 02 | 高郑豪 | CRC | 位串实现写成了“补零版”，标准值算出 `0xA69D` |
| 03 | 高郑豪 | 汉明码 | 展示字符串把 `d1` 写成了布尔表达式 |
| 待补充 | 周恩旭 | 编码 / 信道 | 待补充 |
| 待补充 | 张鑫渝 | 界面 | 待补充 |
| 待补充 | 郑婉欣 | 文档 / 测试 | 待补充 |

---

## 01　奇偶校验：AI 只写了一半

### 1. 提示词

```text
你是 Python 老师。请写两个函数：parity_encode(bits, mode) 和 parity_check(frame, mode)。
mode 是 'even' 或 'odd'。输入位串 str，返回 {ok, result, steps, message}。
steps 是列表，每步 {title, detail}，用中文说明在算什么。只用标准库。
```

### 2. AI 输出

```python
def parity_encode(bits, mode="even"):
    ones = bits.count("1")
    parity = "1" if ones % 2 == 0 else "0"   # 让 1 的个数变成偶数
    frame = bits + parity
    steps = [
        {"title": "统计数据", "detail": f"数据里有 {ones} 个 1"},
        {"title": "补校验位", "detail": f"补上 {parity}，组成 {frame}"},
    ]
    return {"ok": True, "result": {"frame": frame}, "steps": steps, "message": "完成"}
```

### 3. 人工修改

跑验收用例 `1011001` 时，`mode="odd"` 也算出补 `0`，和要求的“奇校验补 1”不一致。查阅后确认 AI **只实现了偶校验**，`mode` 参数根本没被使用。改成显式判断目标奇偶：

```python
def parity_bit_for(data_bits, mode="even"):
    ones = count_ones(data_bits)
    need_odd = (mode == MODE_ODD)          # 奇校验要求 1 的个数是奇数
    parity_is_one = (ones % 2 == 1) != need_odd
    return "1" if parity_is_one else "0"
```

同时补了两处：

1. `mode` 只接受 `'even'` / `'odd'`，其余直接返回 `ok=False`；
2. `steps` 从 2 条扩到 4 条（读入 → 判断补什么 → 组帧 → 复核），否则界面“分步解释”只有两行，看不出过程。

### 4. 反思

AI 的默认行为是**挑最省事的那条分支实现**：奇偶校验里偶校验最常见，它就把 `mode` 当装饰品留着。参数看着齐全、代码也能跑，**错在语义而不是语法**——这类错误编译器不报、运行不崩，只能靠“拿标准用例去撞”。教训是：**凡是带 `mode` / `encoding` 这类开关的函数，必须让每个取值都各有一条测试**。

---

## 02　CRC：位串方向对、细节错，标准值差得很远

### 1. 提示词

```text
写 crc_encode(data, poly, width, init) 和 crc_check(...)。
用模 2 除法逐位异或的竖式，返回每一步的中间余数；不要用查表法，不要位反射。
支持 0x07（CRC-8）、0x8005（CRC-16/IBM）、0x1021（CRC-16/CCITT，初值 0xFFFF）。
```

### 2. AI 输出

```python
def crc_remainder(bits, poly, width, init):
    register = init & ((1 << width) - 1)
    for bit in bits:
        top = register & (1 << (width - 1))     # 先记下最高位
        register = (register << 1) & ((1 << width) - 1)
        register |= int(bit)                    # 再把数据位移进最低位
        if top:
            register ^= poly
    return register
```

注释写得挺像回事，思路“取最高位 → 左移 → 移入数据 → 异或”也确实是模 2 除法的形状。

### 3. 人工修改

按验收要求验 `"123456789"` + `0x1021` + 初值 `0xFFFF`，期望 `0x29B1`，实际得到 **`0xA69D`**。

手工推了前 8 位才发现：这份代码把数据位**移进了寄存器最低位**，等价于“先给数据补 `width` 个 0 再除”的另一种写法；而标准算法是**让寄存器最高位与当前数据位比较**，两者在 `top=1 且 bit=1` 时结果不同——恰恰这一种组合会多异或一次多项式。改成：

```python
for bit in bits:
    top = 1 if register & (1 << (width - 1)) else 0
    if top ^ int(bit):                       # 最高位与数据位不同才异或
        register = ((register << 1) ^ poly) & mask
    else:
        register = (register << 1) & mask
```

改完后三个标准值一次全对：

| 方案 | 多项式 | 初值 | 期望 | 实际 |
| :--- | :--- | :--- | :--- | :--- |
| CRC-16/CCITT | `0x1021` | `0xFFFF` | `0x29B1` | `0x29B1` ✅ |
| CRC-8 | `0x07` | `0x00` | `0xF4` | `0xF4` ✅ |
| CRC-16/IBM | `0x8005` | `0x0000` | `0xFEE8` | `0xFEE8` ✅ |

另外把“整帧再除一次余数为 0”这一步也补上了 `crc_check`——两个方向互相印证，比只看一个余数放心。

### 4. 反思

这是典型的 **AI 幻觉式“看着对”**：变量名、移位、异或、掩码全都在，注释也自洽，但**语义上等价于另一套约定**。CRC 这个算法最坑的地方正是“同一条多项式有四种实现约定”（补零/不补零 × 反射/不反射），AI 混着写完全可能。

唯一的破局办法是**先有标准校验值**（`0x29B1` 这种），再让代码去撞。所以本项目的 `tests/test_crc.py` 把三个标准值写死在断言里——这是回归测试，也是防幻觉的锚点。

---

## 03　汉明码：算得对，但“展示用的那行字”是错的

### 1. 提示词

```text
写 hamming_encode(data_bits) 和 hamming_decode(code_bits)，用 (7,4)：
数据位放第 3、5、6、7 位，校验位放第 1、2、4 位。
decode 要算出伴随式（s4s2s1），它的十进制值就是出错位号，取反即纠正。
返回 {ok, result, syndrome, error_pos, steps, message}。
```

### 2. AI 输出

```python
p1 = d1 ^ d2 ^ d4
p2 = d1 ^ d3 ^ d4
p4 = d2 ^ d3 ^ d4
steps.append({
    "title": f"第 {i} 组 {chunk}",
    "detail": f"p1 = d1⊕d2⊕d4 = {parts['d1']}⊕{parts['d2']}⊕{parts['d4']} = {parts['p1']}；"
              f"p2 = d1⊕d3⊕d4 = {parts['p1'] and parts['d1']}⊕{parts['d3']}⊕{parts['d4']} = {parts['p2']}；"
              f"p4 = d2⊕d3⊕d4 = {parts['d2']}⊕{parts['d3']}⊕{parts['d4']} = {parts['p4']}",
})
```

校验位的**计算**完全正确，7 个位置翻转都能定位。问题在两处：

### 3. 人工修改

**问题一：展示字符串里的 `p1 and d1`。** 上面 `p2` 那行本该写 `d1`，AI 写成了 `{parts['p1'] and parts['d1']}`。Python 里 `1 and 1` 得 `1`，`0 and 1` 得 `0`，看上去**竟然也能打印出 0/1**，肉眼极难发现；但 `p1=1, d1=0` 时会显示成 `0`——正确的 `d1` 明明是 `0`，恰好蒙对，而 `d1=1, p1=1` 时显示 `1` 也对。**只有 `p1=0` 且 `d1=1` 的时候会错**。删掉 `parts['p1'] and`，直接写 `parts['d1']`。

**问题二：无错时 `syndrome` 返回 `None`。** AI 只在“检测到错误”的分支里给 `first_syndrome` 赋值，干净帧走不到那段代码。可是接口约定里写着“无错时伴随式为 0”，界面拿到 `None` 会直接崩在 `syndrome[0]`。修正：

```python
first_syndrome = (0, 0, 0)      # 无错时也要是个三元组，不能是 None
```

补的测试：

```python
def test_syndrome_is_zero_without_error(self):
    result = hamming_decode(self.codeword)
    self.assertEqual(result["syndrome"], (0, 0, 0))
    self.assertEqual(result["error_pos"], 0)
```

### 4. 反思

AI 写算法（数学部分）的能力明显强于写**面向展示的字符串**。它把 `steps` 当成“顺便拼的日志”，不会像对待计算结果那样对待它，于是写出了 `x and y` 这种**语法合法、语义错误、还能打印**的表达式。

这给我们两条规矩：

1. **展示文本也属于被测代码**，不能因为“只是给界面看的”就不测；
2. **接口里承诺的兜底值（0、空列表、空字符串）必须有测试**，否则 AI 只在 happy path 上赋值，边界分支返回 `None`。

第三点体会是关于 `steps` 的设计：一开始以为它是“锦上添花”，后来发现它反而是最容易出 bug 的地方——界面完全依赖它。所以后来定了规矩：**算法返回的每一条 `steps` 都必须和 `result` 用同一批中间变量拼出来**，不能另算一遍，否则两处会慢慢对不上。
