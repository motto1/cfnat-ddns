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
   - 添加cfnat对应containers文件夹下的log文件路径。
   例如：
```bash
    "/mnt/sata1-1/docker/containers/13483dffe8db95d78dd6b600428fafb8e88d0ae09b0d69cc4ccd2cf50179019a/13483dffe8db95d78dd6b600428fafb8e88d0ae09b0d69cc4ccd2cf50179019a-json.log"
 ```

2. 运行脚本：
   ```bash
   python upload.py
   ```
   或者设定crontab定时任务
   ```bash
   0 */1 * * * python /root/upload_natcf.py > /root/natcf.log 2>&1 && echo "Task completed" >> /root/natcf.log
   //每小时执行一次并且生成log日志
   ```

## 注意事项

- 确保日志文件存在且有读取权限
- 确保Cloudflare API Token具有足够的权限
- 只处理443端口的IP地址记录，有需要直接修改程序即可

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
