# AI_Prompts_Log —— AI 结对编程记录

> 记录格式：每位成员 3 条，共 12 条；每条分 **提示词 / AI 输出 / 人工修改 / 反思** 四段。
> 这里只收“**AI 出错、人工抓出来**”的真实案例——照着抄就能跑的那种不写。

| 编号 | 成员 | 模块 | 一句话 |
| :--- | :--- | :--- | :--- |
| 01 | 高郑豪 | 奇偶校验 | AI 只实现了偶校验，`odd` 分支是摆设 |
| 02 | 高郑豪 | CRC | 位串实现写成了“补零版”，标准值算出 `0xA69D` |
| 03 | 高郑豪 | 汉明码 | 展示字符串把 `d1` 写成了布尔表达式 |
| 04 | 周恩旭 | 字符编码 | 整串 GBK 编码，遇到编不了的字符整页崩 |
| 05 | 周恩旭 | 进制转换 | 除基取余把“余数为 0”当终止条件，竖式少一行 |
| 06 | 周恩旭 | 信道对比 | 批量统计不固定种子，各方案帧长不同还共用下标 |
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

---

## 04　字符编码：整串 GBK 编码，遇到编不了的字符整页崩

### 1. 提示词

```text
你是 Python 老师。写 encode_text(text)，逐字符给出码点和 UTF-8 / GBK 字节，
再写 text_to_bitstream(text, encoding) 把整段文本拼成 0/1 位流。
返回 {ok, result, steps, message}，steps 每步 {title, detail}，用中文说明在算什么。
GBK 编不了的字符不要抛异常。字符集只支持 utf-8 和 gbk。只用标准库。
```

### 2. AI 输出

```python
def encode_text(text):
    raw_utf8 = text.encode('utf-8')
    raw_gbk = text.encode('gbk')
    steps = [{'title': '编码完成',
              'detail': f'{text} 的 GBK 是 {raw_gbk.hex()}，共 {len(raw_gbk)} 字节'}]
    return {'ok': True, 'result': {'gbk': raw_gbk}, 'steps': steps, 'message': '完成'}
```

输入 `中文` 时这段代码完全正确：GBK 得到 4 字节，UTF-8 得到 6 字节，两个验收值都对，所以第一眼看不出问题。问题在展示与异常两处，只有换输入才会暴露。

### 3. 人工修改

先按验收点撞了三组输入，差异如下：

| 输入 | 期望 | 初版实际 |
| :--- | :--- | :--- |
| 中文 | 逐字给出码点，每字 GBK 2 字节、UTF-8 3 字节，合计 4 / 6 字节 | 只有一整串 4 字节十六进制，无法对应到单个字 |
| `Net` | 3 字节、24 位位流 | 位流函数没实现，只给了字节串 |
| 一个表情符号 | 整体仍成功，该字符 GBK 为空并给出提示 | 抛 `UnicodeEncodeError`，整段中断 |

**第一处：整串编码，字节数对了但对应关系全丢。** UTF-8 一个汉字 3 字节、GBK 2 字节，都是变长编码；整串编码后只剩下一长串十六进制，界面上没法讲“第几个字对应哪几个字节”，也没法和码点对齐。必须逐字符编码。

**第二处：异常粒度。** 只要有一个字符 GBK 编不了，整句 `encode` 就抛异常，前面的字也一起丢。改成字符粒度兜底，单个字失败只标记该字：

```python
try:
    gbk_raw = char.encode('gbk')
except UnicodeEncodeError:
    gbk_raw = None            # 这个字编不了，记下来，继续后面的字
    gbk_failed.append(char)
```

**第三处：统计口径。** 跳过的字符若按 0 字节混进总数，界面上看不出异常，所以汇总里单独列出“GBK 无法表示”的字符，字节数只累计成功的那部分；每个字符的步骤固定写成“第 n 个字符 X，码点 U+XXXX，UTF-8 = …，GBK = …”，格式统一后界面才能按列对齐。

对应的测试，把两个断言写死：

```python
def test_emoji_gbk_fails_but_utf8_ok(self):
    r = encode_text('😀')
    self.assertTrue(r['ok'])
    self.assertIsNone(r['result']['chars'][0]['gbk']['bytes'])

def test_t02_chinese_byte_counts(self):
    r = encode_text('中文')
    self.assertEqual(r['result']['total_gbk_bytes'], 4)
    self.assertEqual(r['result']['total_utf8_bytes'], 6)
```

### 4. 反思

变长编码的展示类功能，最省事的写法是“整串编码再看字节”。它在常用输入下永远是对的：字节数对、结果对，错的只是“逐字符对应关系”和“异常影响范围”，所以拿常规用例撞不出来，必须换非常规输入。

由此定下两条规矩：一是凡要按字符对齐展示的编码功能，一律逐字符调用编码器，不从整串结果反推；二是异常处理必须落在最小单元上，一个字符失败不能连带整段失败，接口里承诺的“降级为空值”必须写成测试。另外，“只支持 utf-8 和 gbk”这类枚举约束要在入口处显式拒绝非法值，否则传进来一个 `latin-1` 会在更深的地方炸。

---

## 05　进制转换：除基取余把“余数为 0”当成了终止条件

### 1. 提示词

```text
写 dec_to_base(decimal, base)，用除基取余给出竖式，base 支持 2 / 8 / 16。
返回 {ok, result, steps, message}，steps 每步写清“被除数 ÷ 基数 = 商 … 余数”。
验收要求：78 转二进制结果是 1001110，竖式正好 7 行。
```

### 2. AI 输出

```python
digits = []
while n % base != 0:          # 余数为 0 就停
    digits.append(n % base)
    n = n // base
return ''.join(str(d) for d in reversed(digits))
```

这段代码注释和课本说法对得上，跑 100 转二进制还能得到 `1100100`，看起来是对的。

### 3. 人工修改

按验收点跑 78 转二进制，得到 6 行、结果 `001110`，与要求的 `1001110`、7 行不一致。换几个数验证，规律很明显：

| 输入 / 基数 | 期望结果 | 期望行数 | 初版实际 |
| :--- | :--- | :--- | :--- |
| 78 / 2 | `1001110` | 7 | `001110`，6 行 |
| 13 / 2 | `1101` | 4 | `110`，3 行 |
| 5 / 2 | `101` | 3 | `10`，2 行 |
| 0 / 2 | `0` | 1（单独说明） | 空串，0 行 |

原因有两层。一是终止条件写成了“余数为 0”，而课本算法要求“除到商为 0 为止”：78 除到商 1 时余数是 1，再除一次商才变成 0，循环提前退出，所以少两位、少两行。二是循环变量没有真正回代，判断用的还是原数。改成以商为循环变量：

```python
rows = []
while quotient > 0:
    remainder = quotient % base
    rows.append((quotient, remainder, DIGITS[remainder]))
    quotient //= base
text = ''.join(row[2] for row in reversed(rows))
```

另外补了两个边界：数字 0 单独处理，否则循环一次都不进，结果会是空串；负数直接返回 `ok=False` 并说明“本模块只演示非负整数”，符号位交给调用方。反方向的按权展开同样改成“非法字符逐位收集、最后统一报错”，避免一位出错就中途抛异常，界面上前功尽弃。

测试里把结果和行数一起断言，行数才是撞出“提前退出”的关键：

```python
def test_78_to_binary_seven_rows(self):
    r = dec_to_base(78, 2)
    self.assertEqual(r['result']['text'], '1001110')
    self.assertEqual(len(r['result']['remainders']), 7)
```

### 4. 反思

课本一句话“除到商为 0 为止”，落到代码里就是“循环变量选哪个、终止条件描述哪个量”，而这两处恰好都是看起来很顺手的写法。跑 100、跑 5 之外的数都可能对，偏偏在商为 1 的时候少一位，属于典型的“样例能过、验收不过”。

所以验收点不能只给结果，要给“结果 + 行数”双重约束：结果对而少一行的错误，只有行数能撞出来。凡是用 `while` 写的迭代，先确认循环变量有没有真的更新，再看终止条件描述的到底是商还是余数。

---

## 06　信道对比：不固定种子，各方案帧长不同还共用同一组下标

### 1. 提示词

```text
写 inject_error(bits, positions) 和 compare_schemes(data, positions)，把一维奇偶、二维奇偶、
CRC-16/CCITT、Internet 校验和、汉明码 (7,4) 五种方案放在同一段数据上对比检出情况；
再写 batch_compare(data, runs, error_rate, seed) 做批量统计。不要重写这五种算法，直接调用已有的。
验收要求：同一种子跑两次，结果必须完全一致。
```

### 2. AI 输出

```python
for key in SCHEMES:
    frame = build[key](data)
    pos = random.randrange(len(frame))       # 全局 random，没有种子
    corrupted = flip(frame, pos)
    detected = check[key](corrupted)
```

单跑一次看不出毛病，五个方案都能给出“检出 / 未检出”。但把它当实验工具用，四处问题一起冒出来。

### 3. 人工修改

**第一处：可复现性。** 全局 `random` 每次结果都不同，报告里写下的检出率谁也复现不出来，验收点直接不过。改成带种子的生成器，并把本次种子回传到结果里：

```python
rng = random.Random(seed)
positions = [i for i in range(len(frame)) if rng.random() < error_rate]
```

**第二处：下标越界。** 五种方案的帧长并不相同，同一组下标套到不同帧上必然有越界的。以 8 位数据为例：

| 方案 | 帧长 | 合法下标 | 下标 20 是否合法 |
| :--- | :--- | :--- | :--- |
| 一维奇偶 | 9 位（数据 + 1 位校验） | 0 ~ 8 | 越界 |
| 二维奇偶 | 16 位（4 × 4 方阵） | 0 ~ 15 | 越界 |
| CRC-16/CCITT | 24 位（数据 + 16 位余数） | 0 ~ 23 | 合法 |
| Internet 校验和 | 32 位（补齐到 16 位 + 16 位校验和） | 0 ~ 31 | 合法 |
| 汉明码 (7,4) | 14 位（8 位数据分两块） | 0 ~ 13 | 越界 |

所以每个方案都要按自己的帧长规范化下标，去重并排序，越界直接返回提示，而不是让 `flip` 抛异常把整页弄崩：

```python
cleaned = sorted({int(p) for p in positions})
for p in cleaned:
    if not 0 <= p < length:
        raise IndexError(f'位下标 {p} 超出范围 0..{length - 1}')
```

**第三处：长度补齐。** Internet 校验和按 16 位字处理，数据不足 2 字节时尾部补 0 对齐，否则“数据 + 2 字节校验和”凑不够接收端要求的长度；二维奇偶按数据长度的平方根向上取整确定方阵边长，尾部补零凑满方阵，否则组帧时越界。补的都是演示用填充位，不影响判定结论，但必须在步骤里写清楚补了几位。

**第四处：注入语义。** 同一个位置翻两次等于没翻，所以下标要先合并去重；界面上按“第几位”讲、内部按下标算，两个口径要固定，否则“第 2 位”会和“下标 2”错一位。

测试把可复现性写死，同时覆盖重复下标与越界两种边界：

```python
def test_t10_same_seed_same_result(self):
    a = batch_compare(self.data, runs=20, error_rate=0.1, seed=2026)
    b = batch_compare(self.data, runs=20, error_rate=0.1, seed=2026)
    self.assertEqual(a['result']['stats'], b['result']['stats'])
```

### 4. 反思

“批量统计”这类功能的正确性不在单次结果里，而在“别人能不能按同一条件复现你的表”。种子不是附加功能，是设计约束，所以它从第一天就写进接口签名、写进结果字段、写进测试断言。

复用别人写的算法时，最容易被忽略的是“长度口径”：补零补几位、方阵怎么取、按字节还是按 16 位字。这些细节不在函数签名里，只能在编排层逐个适配。五种方案共用一套断言是不现实的，每个方案都要有自己的边界测试，否则越界只会在某一种方案上炸，还未必被跑到。

