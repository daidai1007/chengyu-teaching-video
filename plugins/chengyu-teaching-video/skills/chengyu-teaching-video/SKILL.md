---
name: chengyu-teaching-video
description: Generate finished two-, three-, or four-panel Chinese idiom teaching animations from idioms, meanings, pinyin, sentiment labels, and exercise questions, while matching the bundled reference video's exact mid-century Chinese educational-picture-book style. Use when the user asks to make, replace, revise, or batch-create a 1080×1920 成语辨析/成语教学 video, semantic illustration animations, a Douyin-ready MP4, or a copyable question/answer version.
---

# 成语教学视频生成器

## 接收输入

接受用户提供以下内容：

- 两至四个成语；
- 每个成语的释义；
- 一道或多道题目；答案可省略，能够唯一判断时自行填写。

不要要求用户提供分镜、配图故事或动画方式。根据释义选择最直观、无歧义、可循环的具象故事。依据词项数量自动采用两栏、三栏或四栏，始终按单列从上到下排列。

将规范化输入保存为 UTF-8 JSON。字段格式见 [input-schema.md](references/input-schema.md)。

## 锁定成品规格

默认输出到用户指定的输出目录；用户未指定时，输出到当前工作区的 `output/`：

- `成语教学_<成语1>_<成语2>_<成语3>.mp4`
- `题目可复制_<成语1>_<成语2>_<成语3>.txt`
- `题目可复制_<成语1>_<成语2>_<成语3>.md`
- `三道选择题_<成语1>_<成语2>_<成语3>.png`
- `三道选择题_<成语1>_<成语2>_<成语3>.jpg`
- `成语教学_<成语1>_<成语2>_<成语3>_逐帧检查.jpg`

固定视频参数：

- 1080×1920、9:16；
- 6秒、15fps、90帧；
- H.264 MP4、无水印；
- 固定镜头，无缩放、转场或抖动；
- 所有栏从第1帧同时播放；
- 中文全部用系统真实字体排版，禁止在生成插画时生成文字；
- 左、右、顶部安全边距固定为113像素，内容宽度854像素。

排版必须遵循[统一排版规范](references/layout-spec.md)：标题行包含成语、带声调拼音及【中性/褒义/贬义】，并保持单行；所有栏按纵向单列排列，禁止2×2横向宫格。

## 强制匹配参考画风

把以下资产作为唯一画风依据：

- `assets/style-reference.mp4`
- `assets/style-reference-full.jpg`
- `assets/style-reference-family.png`
- `assets/style-reference-elephant.png`
- `assets/style-reference-rabbit.png`

生成或重绘插画前必须查看完整参考帧和三个裁切参考。插画生成时必须把最相近的裁切参考作为图像参考输入，不能只在提示词中写“复古风”。遵循 [style-lock.md](references/style-lock.md)。

把每幅新插画判断为参考成品同一位插画师、同一套教育卡中的新增画面。只用调色滤镜掩盖造型或笔触差异视为失败。

## 制作流程

### 1. 设计两至四栏语义动画

为每个成语设计一个单场景、单核心关系的动画：

- 让运动关系直接对应释义，例如“连续出现”“一增一减”“交替起落”；
- 让动作从第1帧开始，6秒内形成一次完整、自然的循环；
- 固定背景、地平线、主体根部或主要支点，只移动应当运动的对象；
- 禁止整幅图机械平移、镜像身体、局部融化、忽隐忽现或用无意义粒子代替动作；
- 保持物体真实结构，不为动画方便改变物种、器物或植物的基本构造。

先确定每栏的背景、独立运动对象、锚点、起止状态和循环方式，再制作素材。

### 2. 制作无文字插画素材

用图像生成工具分别创建三栏无文字插画。生成提示必须包含：

- 指定参考图像资产；
- 精确场景、主体数量和结构；
- 20世纪中期中国儿童教育绘本、蛋彩/彩铅/轻质油彩、旧纸印刷颗粒；
- 温暖奶油黄与象牙黄，低饱和墨绿、灰蓝、赭石、浅棕、柔粉；
- 柔和明暗、细密克制笔触、主体结构清晰；
- 明确禁止文字、标志、水印、现代数字概念艺术、厚涂、照片转油画、3D和强电影光。

将背景和运动对象拆成透明图层或稳定的关键姿态。对同一主体制作姿态时始终带上同一基准图，保持轮廓、颜色和细节一致。不要让生成模型一次性生成带中文的完整视频。

### 3. 生成每栏90帧

在工作目录中建立：

```text
panel-frames/
├── 1/
├── 2/
└── 3/
```

每栏输出90张 PNG，按 `000.png` 到 `089.png` 命名。允许先制作关键姿态，再用遮罩、锚点缩放、局部形变和帧间插值生成完整序列。

逐帧检查：

- 背景不漂移；
- 主体不闪烁；
- 轮廓和纹理不跳动；
- 中文区域始终为空；
- 首尾运动状态可平滑衔接；
- 三栏在同一时间轴上同时有合理运动。

### 4. 排版并合成视频

运行：

```powershell
python scripts/compose_video.py --input job.json --panel-frames panel-frames --output-dir "<输出目录>"
```

脚本使用固定版式、真实中文字体、113像素左右及顶部安全边距和H.264编码。成语必须使用`simsun.ttc`宋体并以1px同色描边加粗；拼音和褒贬标注使用`msyhbd.ttc`。不得通过改动模板挤压文字。两栏、三栏和四栏的字号、定位、插画尺寸及分隔线严格采用`references/layout-spec.md`；若释义较长，只在规定范围内缩小释义字号，不缩小成语、拼音或褒贬标注。

### 5. 生成可复制题目

运行：

```powershell
python scripts/make_question_outputs.py --input job.json --output-dir "<输出目录>"
```

保留用户题目原文和标点，不擅自改写。选项只在最上方出现一次；正文从上到下排列题目；同时生成UTF-8 TXT、Markdown、PNG和JPG。答案写入文本文件末尾，不在无答案题图上做红色勾选。

### 6. 验收并返工

运行：

```powershell
python scripts/validate_style.py --panel-frames panel-frames --output-dir qa
```

查看生成的风格报告和并排对照图。再从最终视频抽取第0、45、89帧，与 `assets/style-reference-full.jpg` 并排检查：

- 奶油黄色温；
- 青绿、赭石和粉色的饱和度；
- 笔触粗细与旧印刷颗粒；
- 主体造型的真实、柔和程度；
- 背景复杂度与明暗对比；
- 标题、释义、分隔线和留白比例。

只要新图像像现代油画、照片滤镜或另一套插画，就重新生成或重绘素材。不要仅靠统一滤镜修正。

最终用视频信息工具核对：1080×1920、15fps、90帧、6秒、H.264。核对三个成语、释义和题目没有错字、乱码或漏字后再交付。

## 输出说明

向用户直接提供视频、TXT、Markdown和题图的可点击路径，并展示题图预览。说明已经完成画风并排检查和技术参数核验；不要把中间脚本当作主要交付物。
