# Mediado Telegram Bot 独立微服务

这是一个完全独立的 Telegram 机器人微服务，作为 [Mediado](https://github.com/mylittledou/mediado) (核心 m3u8 下载器) 的前端。
它通过 HTTP API 将下载指令转发给核心程序，自身不执行任何下载操作，从而保证核心下载器的绝对稳定。

## QNAP Container Station (UI 界面) 部署指南

由于本服务**无任何持久化状态** (Stateless)，你不需要配置任何存储卷 (Volumes) 映射，部署非常简单。

### 1. 准备工作
* 通过 Telegram 的 [@BotFather](https://t.me/BotFather) 申请一个 Bot Token。
* 通过 Telegram 的 [@userinfobot](https://t.me/userinfobot) 获取你自己的 User ID (一串数字)，用于权限验证。

### 2. 部署步骤 (使用镜像)

如果你已经配置了 GitHub Actions 自动构建 Docker 镜像并推送到了 Docker Hub (例如 `yourusername/mediabot:latest`)：

1. 打开 QNAP 的 **Container Station** -> **创建 (Create)**。
2. 搜索并拉取你的镜像，或者直接点击右上角的 **创建应用程序 (Create Application)**（如果不想写 yml，选择普通容器创建）。
3. **名称 (Name)**: `media-bot`
4. **镜像 (Image)**: 填写你的镜像名 (如 `yourusername/mediabot:latest`)。
5. **高级设置 (Advanced Settings)** -> **环境 (Environment)**，添加以下环境变量：

| 变量名 | 说明 | 示例值 |
| :--- | :--- | :--- |
| `TG_BOT_TOKEN` | 机器人的 Token (必须) | `123456789:ABCdefGHIjklmNOPQ...` |
| `TG_ALLOWED_USERS` | 允许使用机器人的 User ID (推荐配置，防滥用) | `12345678` (多个用逗号分隔) |
| `MEDIADO_URL` | 核心主程序的访问地址。如果是同一台 NAS，直接填 NAS 的内网 IP 和主程序的端口。 | `http://192.168.1.100:5000` |
| `MEDIADO_USERNAME`| 主程序网页登录的账号 | `admin` |
| `MEDIADO_PASSWORD`| 主程序网页登录的密码 | `password` |

6. **网络 (Network)**: 保持默认的 `NAT` 模式即可，因为机器人主动往外（或往局域网IP）发请求，不需要暴露任何端口。
7. 点击 **创建 (Create)**。

### 3. 持久化目录 (不需要)
本项目是完全无状态的，所有数据都在 `mediado` 核心程序中保存，因此**不需要**配置任何主机目录映射。

---

## 开发者：GitHub Actions 自动构建
本项目包含 `.github/workflows/docker-build.yml` 文件。
当推送到 GitHub 仓库的 `main` 分支时，会自动触发构建。

需要在你的 GitHub 仓库的 **Settings -> Secrets and variables -> Actions** 中添加以下 Secrets：
* `DOCKERHUB_USERNAME`: 你的 Docker Hub 用户名
* `DOCKERHUB_TOKEN`: 你的 Docker Hub 访问令牌 (Access Token)
