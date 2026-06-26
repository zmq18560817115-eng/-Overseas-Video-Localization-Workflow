# 03 产出库（版本化视频归档）

每次拼接 `final-video.mp4` 成功后自动复制到此目录：

```
03_产出库/
  ref-025/
    20260626-111208/
      final-video.mp4
      shots/shot-1..5.mp4
      meta/script-pack.json, storyboard.json, ...
      manifest.json
  产出索引.csv
```

**runs/** 里保留最新工作副本；**03_产出库/** 保留每一次成功产出的历史版本。
