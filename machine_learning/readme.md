---
license: mit
---
## `.pkl` 文件是什么？

PKL = Pickle，是 Python 的一种序列化格式。

简单理解：就是把一个 Python 对象（比如训练好的模型）**"冷冻"保存**到硬盘上，
需要的时候再**"解冻"**加载回来，完全不需要重新训练。

---

## 两个文件分别存了什么？

### `bike_availability_model.pkl`

- 存储了训练好的 Random Forest 模型
- 包含所有学习到的决策树、权重等信息
- 加载后可以直接调用 `.predict()` 进行预测

### `model_features.pkl`

- 存储了特征列表：`['station_id', 'capacity', 'lat', 'lon', 'hour', 'day', 'day_of_week', 'is_weekend', 'avg_temperature', 'avg_humidity', 'avg_pressure']`
- 确保预测时特征的**顺序和名称**与训练时完全一致
- 顺序错了预测结果就会出错

---

## 如何在 Flask 中使用？

```python
import pickle
import pandas as pd

# 1. 加载模型和特征列表（Flask启动时执行一次）
with open('bike_availability_model.pkl', 'rb') as f:
    model = pickle.load(f)

with open('model_features.pkl', 'rb') as f:
    features = pickle.load(f)

# 2. 预测时使用
def predict_bikes(station_id, capacity, lat, lon,
                  hour, day, day_of_week, is_weekend,
                  avg_temperature, avg_humidity, avg_pressure):

    # 构造输入数据，顺序必须与features一致
    input_data = pd.DataFrame([{
        'station_id': station_id,
        'capacity': capacity,
        'lat': lat,
        'lon': lon,
        'hour': hour,
        'day': day,
        'day_of_week': day_of_week,
        'is_weekend': is_weekend,
        'avg_temperature': avg_temperature,
        'avg_humidity': avg_humidity,
        'avg_pressure': avg_pressure
    }])[features]  # 用features确保列顺序正确

    prediction = model.predict(input_data)
    return int(round(prediction[0]))
```

