# ✨ Wuwa Character Setup

A Blender addon for setting up Wuthering Waves characters from start to finish. With a single Quick Setup click, the addon automatically applies shaders, assigns textures, creates outlines, and configures geometry nodes — turning raw model files into fully rigged characters ready for animation in just minutes.

![Blender](https://img.shields.io/badge/Blender-4.2+-orange?logo=blender&logoColor=white)
![License](https://img.shields.io/badge/License-GPL--3.0-blue)
![Version](https://img.shields.io/badge/Version-1.0.0-green)

---

## 📦 Installation

1. Download the addon `.zip` file
2. Open Blender → `Edit` → `Preferences` → `Add-ons`
3. Click `Install from Disk...` → select the `.zip` file
4. Enable **Wuthering Waves Setup Wizard**

> [!NOTE]
> Requires **Blender 4.2** or later.

---

## 🔗 Requirements

- [**UEFormat**](https://github.com/h4lfheart/UEFormat/tree/blender) — Required for importing `.uemodel` files into Blender

---

## 🚀 Quick Start

### Step 1 — Import Model
Install the **UEFormat** addon, then use `File` → `Import` → `Unreal Engine (.uemodel)` to import your character model.

### Step 2 — Quick Setup
Select the character mesh → open the **Wuthering Waves** panel in the sidebar (`N`) → click **Quick Setup**.

The addon will automatically:
- 🎨 Apply Shader & Material
- 🖼️ Assign Textures
- 📐 Set up Geometry Nodes & Outlines

### Step 3 — Customize (Optional)
Use the panel sections below to further enhance your character setup.

---

## 🎯 Features

### 🎨 Material Pipeline
| Feature | Description |
|---|---|
| **Shader Selection** | Choose between Wuthering Waves or Gathering Wives shader |
| **Apply Shader** | One-click shader and material assignment |
| **Import Textures** | Automatic texture detection and assignment |

### 🖼️ Texture Pipeline
| Feature | Description |
|---|---|
| **Normal / Injured / Wet** | Switch between texture status modes |
| **Form Change** | Cycle through available texture form variants |

### 🦴 Character Rig
| Feature | Description |
|---|---|
| **Rigify Armature** | One-click professional rig generation with Rigify |
| **Create Face Panel** | Build facial expression controls with bone drivers |
| **Import Face Panel** | Import pre-made face panel from `.blend` file |

### ⚙️ Global Settings
| Feature | Description |
|---|---|
| **Expression** | Adjust Face Blush, Face Shadow, Face Shadow Atlas |
| **Shadow** | Control Shadow Offset, Shadow Smooth, Cast Shadows |
| **Skin Color** | Set Skin Lit, Midtone, Shadow, Edge colors |

### 🔧 Advanced Tools
| Feature | Description |
|---|---|
| **Set Driver** | Set up shader drivers for light direction and head tracking |
| **Animation Mode** | Toggle lightweight viewport mode for smoother animation playback |
| **Add Tacet Mark** | Add Tacet Mark material with UV setup |
| **Join Mesh** | Merge character mesh parts into one object |
| **Create Collection** | Organize objects into structured collections |
| **Set Up Geometry Nodes** | Configure outlines and geometry node effects |
| **Bone Arrangement** | Organize physical bones (Hair, Skirt, Cloth, Chest, Tail) into collections |
| **Planet Shadow Catcher** | Set up shadow catcher for Planet material |

### ✨ Visual Effects
| Feature | Description |
|---|---|
| **Outlines Toggle** | Toggle character outlines on/off |
| **Two-Colored Eyes** | Enable/disable heterochromia effect |
| **Animate Tacet Mark** | Toggle Tacet Mark animation with custom driver expression |

### 🎥 Smart Camera System
| Feature | Description |
|---|---|
| **Smart Camera** | Auto-positioned camera with portrait presets (M, MS, S, XL, XXL) |

### 🔧 AMD Material Fix
| Feature | Description |
|---|---|
| **Linear / Cubic** | Fix texture interpolation issues on AMD GPUs |

---

## 📍 Panel Location

Blender Sidebar (`N`) → Tab **Wuthering Waves**

---

## 📄 License

GPL-3.0 — See [LICENSE](LICENSE) for details.

## 👤 Credits

**Akatsuki** — Version 1.0

This project was developed with the help of many public guides, documentation, and examples from the community. Sincere thanks to the original authors for sharing their knowledge.

Special thanks to **Jonn**, **Scheinze**, **Micchi**, and **Fnoji** from the **Omatsuri** Discord server.
