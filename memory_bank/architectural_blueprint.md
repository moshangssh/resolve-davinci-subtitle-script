# 架构蓝图：重构为 FastAPI + Tauri + React

这是一个高阶架构图，展示了将现有应用重构为现代化、前后端分离架构的计划。

```mermaid
graph TD
    subgraph "用户桌面环境"
        subgraph "Tauri 应用"
            direction LR
            subgraph "Rust 核心 (Tauri Main Process)"
                TauriCore[Tauri Core] -- 管理生命周期 --> FastAPIProcess(FastAPI 子进程)
                TauriCore -- 提供原生API --> Frontend
            end

            subgraph "前端 (WebView)"
                Frontend[React UI] -- HTTP API 请求 --> FastAPIProcess
            end
        end

        subgraph "DaVinci Resolve 环境"
            Resolve[DaVinci Resolve]
        end
    end

    subgraph "后端服务 (在Tauri子进程中运行)"
        direction TB
        FastAPIProcess -- Python脚本API --> Resolve
        FastAPIProcess -- 提供RESTful API --> Frontend
        FastAPIProcess -- 封装 --> BusinessLogic[业务逻辑 (原services.py)]
        BusinessLogic -- 依赖 --> SubtitleManager[字幕管理 (subtitle_manager.py)]
        BusinessLogic -- 依赖 --> ResolveIntegration[Resolve集成 (resolve_integration.py)]
        BusinessLogic -- 依赖 --> FormatConverter[格式转换 (format_converter.py)]
    end

    style Frontend fill:#cde4ff
    style TauriCore fill:#f9f,stroke:#333,stroke-width:2px
    style FastAPIProcess fill:#ffc,stroke:#333,stroke-width:2px
    style Resolve fill:#bbf,stroke:#333,stroke-width:2px
```

## 核心组件职责

*   **Tauri Core (Rust):**
    *   **应用入口:** 启动和管理整个应用的生命周期。
    *   **进程管理:** 负责在后台启动和监控 FastAPI 后端服务作为一个子进程。
    *   **原生 API 桥梁:** 为前端提供访问原生操作系统功能的接口 (如文件对话框、通知等)。
    *   **窗口管理:** 创建和管理应用的 WebView 窗口。

*   **React UI (JavaScript/TypeScript):**
    *   **用户界面:** 替换所有现有的 `PySide6` UI，提供一个现代、响应式的用户体验。
    *   **状态管理:** 使用如 Redux, Zustand 或 React Context 等工具管理前端状态。
    *   **API 消费:** 通过 `fetch` 或 `axios` 等库，向本地运行的 FastAPI 服务发起 HTTP 请求，以获取数据和触发后端操作。

*   **FastAPI 子进程 (Python):**
    *   **Web API:** 提供一个 RESTful API (例如 `/api/subtitles`, `/api/tracks`, `/api/resolve/reimport`) 供前端调用。
    *   **业务逻辑封装:** 将现有 `src/services.py`, `src/ui_logic.py` 等模块中的核心业务逻辑迁移到 FastAPI 的路由处理函数或服务类中。
    *   **Resolve 通信:** 保留并继续使用 `resolve_integration.py` 来与 DaVinci Resolve 的脚本 API 进行通信。所有与 Resolve 的直接交互都应被限制在 FastAPI 后端。
    *   **数据管理:** 继续使用 `subtitle_manager.py` 和 `format_converter.py` 等模块来处理字幕数据的核心逻辑。

## 数据流示例 (查找替换)

1.  用户在 React UI 的输入框中输入查找和替换的文本，点击“全部替换”按钮。
2.  React UI 发起一个 `POST` 请求到 `http://localhost:PORT/api/subtitles/replace-all`，请求体中包含 `{ "find": "textA", "replace": "textB" }`。
3.  FastAPI 后端接收到请求，调用相应的业务逻辑。
4.  业务逻辑使用 `SubtitleManager` 在内存（或缓存文件）中执行替换操作。
5.  操作完成后，FastAPI 返回成功响应，可能包含更新后的字幕数据。
6.  React UI 接收到响应，更新其前端状态，重新渲染字幕列表以显示变更。


---

## 后端重构详细规划 (FastAPI)

此部分详细说明了将现有 Python 逻辑迁移到 FastAPI 应用的步骤和规范。

### 1. 新项目结构

建议创建一个新的 `backend` 目录来存放所有与 FastAPI 相关的代码，与现有的 `src` 和未来的 `frontend` 目录并列。

```
/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用实例和路由
│   │   ├── api/                # API 路由模块
│   │   │   ├── __init__.py
│   │   │   ├── subtitles.py
│   │   │   └── timeline.py
│   │   ├── core/               # 配置, 核心依赖
│   │   │   ├── __init__.py
│   │   │   └── dependencies.py
│   │   ├── models/             # Pydantic 模型
│   │   │   ├── __init__.py
│   │   │   └── subtitle.py
│   │   └── services/           # 业务逻辑服务 (从原 src/ 迁移)
│   │       ├── __init__.py
│   │       ├── resolve_integration.py
│   │       ├── subtitle_manager.py
│   │       └── format_converter.py
│   ├── tests/                  # 后端单元测试
│   └── requirements.txt        # Python 依赖
├── frontend/                   # React + Tauri 前端代码
├── memory_bank/
└── src/                        # (将被逐步废弃)
```

### 2. 依赖项 (`requirements.txt`)

```
fastapi
uvicorn[standard]
pydantic
python-multipart  # 用于文件上传 (导入SRT)
# 现有依赖
cffi
```

### 3. API Endpoints 定义

我们将根据现有功能定义一组 RESTful API。

**Timeline API (`/api/timeline`)**

*   `GET /tracks`: 获取所有可用的字幕轨道列表。
    *   **响应:** `List[Track]`
*   `GET /info`: 获取当前时间线信息（帧率，起始时间码等）。
    *   **响应:** `TimelineInfo`

**Subtitles API (`/api/subtitles`)**

*   `GET /{track_id}`: 获取指定轨道的所有字幕。
    *   **响应:** `List[Subtitle]`
*   `PUT /{track_id}/{subtitle_id}`: 更新单个字幕的文本内容。
    *   **请求体:** `SubtitleUpdate`
    *   **响应:** `Subtitle` (更新后的字幕)
*   `POST /replace-all`: 在当前轨道执行“全部替换”。
    *   **请求体:** `ReplaceRequest`
    *   **响应:** `List[Subtitle]` (更新后的字幕列表)
*   `POST /import-srt`: 通过上传 SRT 文件内容来导入字幕。
    *   **请求体:** `multipart/form-data` with file content.
    *   **响应:** `List[Subtitle]` (导入的字幕列表)
*   `POST /export-srt/{track_id}`: 导出指定轨道的字幕为 SRT 文件。
    *   **响应:** `StreamingResponse` (文件流)
*   `POST /reimport-to-resolve`: 将当前缓存的字幕重新导入到达芬奇。
    *   **响应:** `StatusResponse`

### 4. Pydantic 数据模型 (`backend/app/models/`)

使用 Pydantic 模型进行数据验证和序列化。

```python
# backend/app/models/subtitle.py
from pydantic import BaseModel
from typing import List, Optional

class Subtitle(BaseModel):
    id: int
    text: str
    start_timecode: str
    end_timecode: str
    start_frames: int
    end_frames: int

class SubtitleUpdate(BaseModel):
    text: str

class ReplaceRequest(BaseModel):
    find_text: str
    replace_text: str
    case_sensitive: bool

class Track(BaseModel):
    id: int
    name: str

class TimelineInfo(BaseModel):
    frame_rate: float
    start_timecode: str

class StatusResponse(BaseModel):
    success: bool
    message: Optional[str] = None
```

### 5. 依赖注入 (`backend/app/core/dependencies.py`)

FastAPI 的依赖注入系统是管理服务实例的理想方式。

```python
# backend/app/core/dependencies.py
from functools import lru_cache
from ..services.resolve_integration import ResolveIntegration
from ..services.subtitle_manager import SubtitleManager

@lru_cache()
def get_resolve_integration() -> ResolveIntegration:
    return ResolveIntegration()

@lru_cache()
def get_subtitle_manager() -> SubtitleManager:
    # 可能需要修改 SubtitleManager 的初始化方式
    return SubtitleManager()

# 在 API 路由中使用:
# @router.get("/tracks")
# def get_tracks(resolve_svc: ResolveIntegration = Depends(get_resolve_integration)):
#     return resolve_svc.get_subtitle_tracks()
```

### 6. 现有逻辑迁移

*   将 `src` 目录下的 `resolve_integration.py`, `subtitle_manager.py`, `format_converter.py`, `timecode_utils.py` 等核心逻辑文件移动到 `backend/app/services/`。
*   移除这些文件中所有与 `PySide6` 相关的代码和依赖。
*   修改 `SubtitleManager` 和 `ResolveIntegration` 的方法，使其返回 Pydantic 模型而不是字典或自定义对象。
*   将 `main.py` 和 `services.py` 中的业务逻辑（即事件处理器和应用服务中的方法）重构为 FastAPI 路由函数中的逻辑。

### 7. 错误处理

在 FastAPI 中创建一个全局的异常处理器，以捕获在业务逻辑中可能出现的特定异常（例如 `ResolveConnectionError`），并将其转换为标准化的 HTTP 错误响应。

```python
# backend/app/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

class ResolveConnectionError(Exception):
    pass

app = FastAPI()

@app.exception_handler(ResolveConnectionError)
async def resolve_connection_exception_handler(request: Request, exc: ResolveConnectionError):
    return JSONResponse(
        status_code=503,
        content={"message": "无法连接到 DaVinci Resolve。请确保 Resolve 正在运行。"},
    )
```


---

## 前端重构详细规划 (Tauri + React)

此部分详细说明了如何使用 Tauri 和 React 构建一个全新的、现代化的前端界面。

### 1. 技术栈选型

*   **框架:** React (使用 Vite 作为构建工具，以获得最佳的开发体验和性能)。
*   **语言:** TypeScript。强制使用 TypeScript 可以极大地提高代码质量和可维护性。
*   **UI 组件库:** 推荐使用 [Shadcn/UI](https://ui.shadcn.com/)。它不是一个传统的组件库，而是提供了一系列可复制粘贴、可定制的组件，非常灵活，并且与 Tailwind CSS 完美集成。这能让我们快速构建出漂亮且一致的界面。
*   **状态管理:** [Zustand](https://github.com/pmndrs/zustand)。它是一个轻量级、快速、样板代码极少的状态管理库，对于中小型应用来说比 Redux 更简单、更易于上手。
*   **数据请求:** [TanStack Query (React Query)](https://tanstack.com/query/latest)。它极大地简化了数据获取、缓存、同步和更新的复杂性，能自动处理加载状态、错误状态，并提供开箱即用的缓存和后台刷新机制。
*   **CSS:** [Tailwind CSS](https://tailwindcss.com/)。它是一个功能优先的 CSS 框架，可以让我们快速构建任何设计，而无需离开 HTML。

### 2. 项目初始化

使用 Tauri 官方的 `create-tauri-app` CLI 工具可以轻松地初始化一个集成了 React + TypeScript + Vite 的项目。

```bash
npm create tauri-app@latest
# 跟随提示选择:
# App name: subvigator-next
# Choose which language to use for your frontend: TypeScript / JavaScript
# Choose your UI template: React
```

### 3. 组件结构 (`frontend/src/components/`)

我们可以根据现有 UI 的功能区域来划分组件。

```
frontend/src/
├── App.tsx                 # 主应用组件，包含整体布局
├── main.tsx                # React 入口文件
├── components/
│   ├── layout/
│   │   ├── MainLayout.tsx    # 主要布局 (包含侧边栏和主内容区)
│   │   └── Header.tsx        # 应用头部
│   ├── subtitles/
│   │   ├── SubtitleTable.tsx # 字幕表格 (核心组件)
│   │   ├── SubtitleRow.tsx   # 表格中的每一行
│   │   └── Timecode.tsx      # 可编辑的时间码组件
│   ├── inspector/
│   │   ├── InspectorPanel.tsx # 右侧检查器面板
│   │   ├── FilterGroup.tsx    # 筛选功能区
│   │   └── FindReplaceGroup.tsx # 查找替换功能区
│   └── ui/                     # 通用UI组件 (由 Shadcn/UI 提供)
│       ├── Button.tsx
│       ├── Input.tsx
│       └── ...
├── hooks/
│   └── useSubtitles.ts       # 自定义 Hook，封装与字幕相关的 React Query 逻辑
└── store/
    └── useAppStore.ts        # Zustand store，用于管理全局UI状态
```

### 4. 状态管理 (`frontend/src/store/` 和 `hooks/`)

*   **服务器状态 (Server State):** 所有从 FastAPI 后端获取的数据（如字幕列表、轨道列表）都应该由 **TanStack Query** 管理。这包括缓存、重新验证等。
*   **客户端状态 (Client State):** 应用的 UI 状态（如当前选中的轨道ID、筛选器的输入文本、查找/替换的输入文本、UI加载状态等）应该由 **Zustand** 管理。

**示例 Zustand Store (`useAppStore.ts`):**

```typescript
import { create } from 'zustand';

interface AppState {
  selectedTrackId: number | null;
  filterText: string;
  findText: string;
  replaceText: string;
  // ... 其他UI状态
  setSelectedTrackId: (trackId: number) => void;
  // ... 其他 actions
}

export const useAppStore = create<AppState>((set) => ({
  selectedTrackId: null,
  filterText: '',
  findText: '',
  replaceText: '',
  setSelectedTrackId: (trackId) => set({ selectedTrackId: trackId }),
  // ...
}));
```

**示例 TanStack Query Hook (`useSubtitles.ts`):**

```typescript
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSubtitles, updateSubtitle } from '../api'; // 假设的 API 调用函数

export const useSubtitles = (trackId: number) => {
  const queryClient = useQueryClient();

  const { data, isLoading, isError } = useQuery({
    queryKey: ['subtitles', trackId],
    queryFn: () => fetchSubtitles(trackId),
    enabled: !!trackId, // 只有当 trackId 存在时才执行查询
  });

  const updateMutation = useMutation({
    mutationFn: updateSubtitle,
    onSuccess: () => {
      // 成功后使缓存失效，自动重新获取最新数据
      queryClient.invalidateQueries({ queryKey: ['subtitles', trackId] });
    },
  });

  return { subtitles: data, isLoading, isError, updateSubtitle: updateMutation.mutate };
};
```

### 5. 与 Tauri 的集成 (`src-tauri/`)

*   **启动 FastAPI 子进程:** 在 `src-tauri/src/main.rs` 中，使用 Tauri 的 `Command` API 来启动打包好的 Python 后端可执行文件。
*   **原生文件对话框:** 对于“导入SRT”和“导出SRT”功能，我们将使用 Tauri 的 `dialog` API 来打开原生的文件选择和保存对话框，而不是依赖浏览器的 `<input type="file">`。

**示例 Tauri 命令 (`src-tauri/src/main.rs`):**

```rust
use tauri::api::dialog::FileDialogBuilder;

#[tauri::command]
async fn open_srt_file() -> Option<String> {
  let file_path = FileDialogBuilder::new()
    .add_filter("SRT Files", &["srt"])
    .pick_file();

  if let Some(path) = file_path {
    // 读取文件内容并返回
    // 注意：更好的做法是让Rust读取文件并返回内容，而不是仅返回路径
    // 以避免在JS中处理文件系统的复杂性
    match std::fs::read_to_string(path) {
        Ok(contents) => Some(contents),
        Err(_) => None,
    }
  } else {
    None
  }
}

fn main() {
    // ...
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![open_srt_file])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
```

在 React 中，可以通过 `@tauri-apps/api/tauri` 包来调用这个命令。


---

## 分阶段实施路线图

为了确保重构过程平稳、可控且风险最低，建议采用以下分阶段的实施策略。

### 阶段 0: 环境搭建与项目初始化 (1-2天)

**目标:** 创建项目骨架，并验证 Tauri, React, FastAPI 三者之间最基础的通信。

1.  **创建目录结构:** 建立顶层的 `backend` 和 `frontend` 目录。
2.  **初始化前端:** 在 `frontend` 目录中，使用 `npm create tauri-app@latest` 创建一个 React + TypeScript + Vite 的 Tauri 项目。
3.  **初始化后端:** 在 `backend` 目录中，按照 FastAPI 的标准方式创建项目结构，并建立 `requirements.txt`。
4.  **验证 Sidecar 模式:**
    *   在 FastAPI 中创建一个简单的 "Hello World" 路由 (例如 `GET /` 返回 `{"message": "Hello from FastAPI"}` )。
    *   配置 `src-tauri/tauri.conf.json`，将 FastAPI 应用（此时可直接用 `uvicorn` 运行）作为一个 `sidecar` 子进程。
    *   在 React 应用中，使用 `fetch` 调用该接口，并验证是否能成功获取到消息。
    *   **里程碑:** 应用可以成功启动，前端能够从后端获取数据。

### 阶段 1: 后端 API 开发 (使用模拟数据) (5-7天)

**目标:** 完全实现 FastAPI 的所有 API 端点，但暂时不与 DaVinci Resolve 交互，而是使用模拟数据。这使得前后端可以并行开发。

1.  **迁移核心逻辑:** 将 `src` 目录下的 `subtitle_manager.py`, `format_converter.py`, `timecode_utils.py` 等非UI、非Resolve的逻辑模块迁移到 `backend/app/services/`。
2.  **移除UI依赖:** 清理这些模块中所有对 PySide6 的依赖。
3.  **实现 Pydantic 模型:** 在 `backend/app/models/` 中创建所有必要的 Pydantic 模型。
4.  **构建 API 路由:** 在 `backend/app/api/` 中实现所有规划好的 API 路由。
5.  **创建模拟服务:** 创建一个 `MockResolveIntegration` 类，它实现与 `ResolveIntegration` 相同的接口，但返回的是硬编码的、可预期的模拟数据（例如，固定的轨道列表、字幕数据等）。
6.  **编写单元测试:** 为所有服务和 API 端点编写 `pytest` 单元测试，确保业务逻辑的正确性。
7.  **里程碑:** 一个功能完整的、但与 Resolve 解耦的后端 API 开发完成，并有文档（FastAPI 自动生成的 Swagger UI）。

### 阶段 2: 前端 UI 开发 (3-5天)

**目标:** 基于第一阶段完成的后端 API，开发一个功能完整的用户界面。

1.  **搭建组件骨架:** 根据规划的组件结构，创建所有 React 组件文件。
2.  **实现状态管理:** 设置 Zustand store 和 TanStack Query 的基础配置。
3.  **开发 UI 组件:** 使用 UI 组件库 (如 Shadcn/UI) 和 Tailwind CSS 构建界面。
4.  **连接 API:** 在组件和 Hook 中，调用在第一阶段中定义好的后端 API。由于后端返回的是可预测的模拟数据，前端开发可以独立、高效地进行。
5.  **集成 Tauri API:** 对于需要原生功能的地方（如文件对话框），调用 Tauri 的 `invoke` 方法。
6.  **里程碑:** 用户界面开发完成，所有功能在连接模拟后端的情况下均可正常工作。

### 阶段 3: 后端与 Resolve 集成 (2-3天)

**目标:** 将后端的模拟数据层替换为与 DaVinci Resolve 的真实交互。

1.  **迁移 `ResolveIntegration`:** 将 `src/resolve_integration.py` 迁移到 `backend/app/services/`。
2.  **切换依赖注入:** 在 FastAPI 的依赖注入系统中，将 `MockResolveIntegration` 切换为真实的 `ResolveIntegration`。
3.  **适配与重构:** 根据需要重构 `ResolveIntegration` 中的方法，使其返回 Pydantic 模型，并处理与真实 Resolve API 通信时可能出现的各种异常。
4.  **集成测试:** 在连接真实 DaVinci Resolve 的情况下，手动或通过脚本测试所有 API 端点，确保其行为符合预期。
5.  **里程碑:** 后端现在可以与 DaVinci Resolve 进行完整的、真实的交互。

### 阶段 4: 端到端集成与测试 (2-3天)

**目标:** 将开发完成的前端与已经连接到 Resolve 的后端进行联调，并修复所有问题。

1.  **联调:** 启动完整的应用程序，进行全面的功能测试。
2.  **识别和修复 Bug:** 重点关注前后端数据格式不匹配、错误处理、边界条件等问题。
3.  **用户体验优化:** 对应用的响应速度、视觉效果和交互流程进行微调。
4.  **里程碑:** 一个功能完整、稳定且通过端到端测试的应用程序。

### 阶段 5: 打包与分发 (1-2天)

**目标:** 将应用打包成可供最终用户使用的、跨平台的分发包。

1.  **打包后端:** 使用 `PyInstaller` 或类似工具将整个 FastAPI 应用（包括所有依赖）打包成一个单一的可执行文件。
2.  **配置 Tauri Bundler:** 更新 `src-tauri/tauri.conf.json`，将打包好的后端可执行文件作为 `sidecar` 资源，并配置正确的启动命令。
3.  **构建应用:** 运行 `npm run tauri build` 命令。
4.  **测试分发包:** 在干净的虚拟机或另一台计算机上安装并测试生成的分发包（`.msi`, `.dmg`, `.AppImage` 等），确保其可以独立运行。
5.  **里程碑:** 生成最终的可分发产品。
