# CFnat DDNS 自动更新工具

这个工具用于自动从cfnat-docker的日志文件中提取IP地址并更新Cloudflare DNS记录。

## 功能特点

- 读取指定日志文件的最后100行
- 提取符合格式的IP地址（例如：104.19.244.253:443）
- 自动更新Cloudflare DNS记录

## 使用方法

1. 首先配置以下变量：
   - `API_TOKEN`: Cloudflare API Token
   - `ZONE_ID`: Cloudflare Zone ID
   - `DOMAIN`: 要更新的域名

2. 运行脚本：
   ```bash
   python upload.py
   ```

## 注意事项

- 确保日志文件存在且有读取权限
- 确保Cloudflare API Token具有足够的权限
- 只处理443端口的IP地址记录

## 错误处理

脚本包含完整的错误处理机制：
- 文件读取错误处理
- API请求错误处理
- 数据解析错误处理

## 监控和日志

脚本会在控制台输出操作状态：
- DNS记录更新成功信息
- 错误信息
- 处理状态信息 
