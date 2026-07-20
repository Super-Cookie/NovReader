**专为本地小说设计的一款阅读软件，让用户在window上可以更舒适地阅读和管理本地小说**</br>
对比市面上一般的 window 端小说本地阅读软件，除了常见的`章节解析`、`目录解析`、`最近阅读`外，还有以下亮点：

## 【亮点】

### 一. 【管理亮点】自定义 `.nov` 文件格式，方便本地小说文件管理和编辑

**📌 解决了什么痛点？**

【1】 本地小说以 *.txt* 存在为主，容易和其他文本文件混在一起，**分不清谁是谁**</br>
✅ `.nov` 使用专属小说图标，用户可以一眼认出小说文件 </br>

【2】 主流 Windows 阅读器需要导入文件才能打开，**不符合轻量化使用习惯**</br>
✅ 双击 `.nov` 直接进入软件阅读，无需额外导入 </br>

【3】 将 *.txt* 转化为 *.epub* 虽然也能够解决前两个问题，但是由于下载的小说难免存在错别字或排版问题</br>
&nbsp; &nbsp; &nbsp; &nbsp; 所以经常需要人工轻量级修订， **而 .epub 内部格式复杂，用户想要修改非常不方便** </br>
✅ 使用自定义格式 `.nov`，右键用记事本打开即可轻松编辑订正</br>

<img width="200" height="100" alt="image" src="https://github.com/user-attachments/assets/7f5454f8-bd55-40ce-b39f-835dd4af8a59" />



---

### 二. 【阅读亮点】悬浮目录支持多列显示，支持分卷、分页，方便上千章节的小说的跳转

**📌 解决了什么痛点？**

【1】 网文动不动上千章</br>
`但是几乎所有window阅读软件，都只针对章节较少的实体书进行设计：即一行通常只显示一个章节`</br>
作为读者**目录跳转非常不方便**</br> 
✅ 一行显示多个章节，充分利用电脑大屏幕，跳转更方便</br>

【2】 很多小说**明明有分卷，但本地阅读器基本都不显示**</br>
&nbsp; &nbsp; &nbsp; &nbsp; 当出现上千个章节的独立标题，会出现难以掌握超长小说剧情的脉络</br>
✅ 支持按分卷信息划分  &nbsp; ✅ 即使小说没有分卷，也会自动对章节进行分页</br>

<img width="1186" height="736" alt="image" src="https://github.com/user-attachments/assets/9ea3b8db-c848-4a1a-9efc-6566cd8bd363" />


---

### 三. 【阅读亮点】长段落自动拆分，阅读更舒适

**📌 解决了什么痛点？**

【1】 不少网文排版粗糙，五六七八行文字揉成一团，密密麻麻的，阅读不是很舒适</br>
【2】 一些偏老派写法的传统实体风格小说，习惯使用长句长段进行描写，阅读比较拗口难懂

✅通过自动拆解长段落，使段落长短错落有致，从而提高读者的阅读浏览体验</br>

<img width="1613" height="744" alt="image" src="https://github.com/user-attachments/assets/7e94387a-9392-4b11-9f10-e9eedb6f4a50" />


---

### 四. 更多细节功能

- 键盘 **左右键** 翻章节，**上下键** 滚动页面，**回车键** 唤出目录
- 深度用户：*config.py* 里可以自定义更多字体、字号、颜色、间距，怎么习惯怎么来

---

## 【使用】

- **打开 `.nov` 小说**：从 *Realease* 里下载 *NovReader_Setup.exe* 后安装即可</br>
  1️⃣NovReader_Setup.exe 不会自动恢复上次打开的小说</br>
  2️⃣NovReader_Setup_RestoreOpened.exe 每次会自动恢复上次打开的小说
- **将 `.txt` 转化为 `.nov`**：</br>
1️⃣单个文件 直接修改文件格式后缀为 *.nov* 即可</br>
2️⃣多个文件 可以下载*Realease* 里面的 TxtToNov.bat批量修改
- **绑定`NovReader`为默认的`.nov`打开程序**：</br>
部分window版本由于安全原因，安装后不能自动绑定成功</br>
需要用户手动打开 *.nov* 文件的右键菜单，选择属性，然后修改打开方式为 *NovReader* 即可

---

## 【协议遵循】

本项目采用 **双协议模式**：

### ① 非商业使用 — AGPL-3.0

```
GNU AFFERO GENERAL PUBLIC LICENSE
Version 3, 19 November 2007

Copyright (C) 2026 NovReader

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU Affero General Public License for more details.
```

**AGPL-3.0 核心要求：**

1. 📖 **源码可见** — 你有权查看、修改本软件的完整源码
2. 🔁 **修改须开源** — 如果你修改了代码并对外分发/提供服务，修改后的源码也必须以 AGPL-3.0 公开
3. 🌐 **网络服务也视同分发** — 即使你不发安装包，只是把改过的版本部署在服务器上通过网页提供服务，也必须开放源码（这是 AGPL 比 GPL 严格的地方）
4. ⚖️ **保留版权** — 任何分发都必须保留原作者信息和协议声明

**适用范围（免费 ✅）：**

- ✅ 个人学习、自用阅读
- ✅ 非营利组织内部使用
- ✅ 个人修改并在 GitHub 等平台开源发布
- ✅ 教育、学术研究

### ② 商业使用 — 需购买商业授权

**适用范围（付费 💰）：**

- ❌ 企业/公司内部批量部署，不对外公开源码
- ❌ 将本软件集成到商业产品中销售
- ❌ 基于本软件二次开发后作为付费产品提供
- ❌ 以盈利为目的、且不愿公开修改后源码的使用场景

> 📧 商业授权请联系作者，获取报价和授权条款。

---

*SPDX-License-Identifier: AGPL-3.0 OR Commercial*
