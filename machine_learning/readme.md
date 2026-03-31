# Machine Learning Notebook

这个目录包含用于预测 Dublin Bikes 站点可用单车数量的训练 notebook：

- Notebook: `ml.ipynb`
- 在线模型地址: <https://huggingface.co/ucdse/bike_availability_model/tree/main>

## Notebook 作用

`ml.ipynb` 用于完成一个完整的机器学习训练流程，主要包括：

- 读取并检查训练数据 `final_merged_data.csv`
- 做基础 EDA，包括缺失值和目标变量分布查看
- 选择有效特征并构造衍生特征
- 训练并比较多个回归模型
- 保存表现最好的模型和对应特征列表

Notebook 中对比的模型包括：

- Linear Regression
- Decision Tree Regressor
- Random Forest Regressor
- Gradient Boosting Regressor

当前 notebook 中最终保存的是表现最好的 `Random Forest` 模型。

## 使用方法

### 1. 准备环境

建议使用 Python 3.10+，并安装 notebook 运行所需依赖：

```bash
pip install jupyter pandas numpy matplotlib seaborn scikit-learn joblib
```

### 2. 准备数据

将训练数据文件 `final_merged_data.csv` 放在和 `ml.ipynb` 同一目录下，也就是 `machine_learning/` 目录中。

Notebook 默认通过下面的方式读取数据：

```python
df = pd.read_csv('final_merged_data.csv')
```

所以如果文件名或路径不同，需要同步修改 notebook 中的读取代码。

### 3. 运行 notebook

进入项目目录后启动 Jupyter：

```bash
jupyter notebook
```

然后打开 `machine_learning/ml.ipynb`，按照单元格从上到下依次运行即可。

如果你使用 VS Code，也可以直接打开该 notebook 并顺序执行所有 cells。

## 运行输出

notebook 执行完成后，会在当前目录生成以下文件：

- `bike_availability_model.pkl`：训练好的最佳模型
- `model_features.pkl`：模型训练时使用的特征列表

这两个文件可以直接给 Flask 应用加载，用于后续预测。

## Notebook 主要流程

整个 notebook 大致分为以下几个阶段：

1. 数据加载与初步检查
2. 缺失值和目标变量分析
3. 特征选择
4. 特征工程
5. 相关性分析
6. 划分训练集和测试集
7. 模型训练与效果对比
8. 特征重要性分析
9. 保存最佳模型

## 模型地址

如果不想本地重新训练，也可以直接查看或下载已经上传的模型文件：

<https://huggingface.co/ucdse/bike_availability_model/tree/main>
