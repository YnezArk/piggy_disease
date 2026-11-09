# -*- coding: utf-8 -*-
"""
CNN-BiLSTM 融合模型（设计文档 3.4 节 / 付小朋等，2026）：
  输入 (T, F, 1) 特征矩阵
  -> Conv2D(32, 3x3)+ReLU+MaxPool(2x2)
  -> Conv2D(64, 3x3)+ReLU+MaxPool(2x2)
  -> TimeDistributed(Flatten)      # 展平每个时间步上的空间特征，交给时序网络
  -> BiLSTM(64, return_sequences=True)
  -> BiLSTM(32)
  -> Dense(64, ReLU) -> Dropout(0.3) -> Dense(2, Softmax)
"""
from __future__ import annotations

import tensorflow as tf
from tensorflow.keras import layers, models, regularizers

import config


def build_cnn_bilstm(input_shape=config.INPUT_SHAPE,
                     num_classes=config.NUM_CLASSES,
                     cnn_filters=config.CNN_FILTERS,
                     kernel_size=config.KERNEL_SIZE,
                     pool_size=config.POOL_SIZE,
                     lstm_units=config.LSTM_UNITS,
                     dense_units=config.DENSE_UNITS,
                     dropout=config.DROPOUT_RATE,
                     l2=1e-4):
    """构建 CNN-BiLSTM 模型。

    Parameters
    ----------
    input_shape : tuple
        (时间帧数, 特征维度, 1)
    """
    inputs = layers.Input(shape=input_shape, name="input")

    # ---- CNN 部分：局部频谱模式（空间特征）----
    x = layers.Conv2D(cnn_filters[0], kernel_size, activation="relu",
                      padding="same", kernel_regularizer=regularizers.l2(l2),
                      name="conv1")(inputs)
    x = layers.MaxPooling2D(pool_size, name="pool1")(x)

    x = layers.Conv2D(cnn_filters[1], kernel_size, activation="relu",
                      padding="same", kernel_regularizer=regularizers.l2(l2),
                      name="conv2")(x)
    x = layers.MaxPooling2D(pool_size, name="pool2")(x)

    # ---- 过渡层：把每个时间步上的空间特征展平为特征向量 ----
    x = layers.TimeDistributed(layers.Flatten(), name="time_distributed_flatten")(x)

    # ---- BiLSTM 部分：时序依赖建模 ----
    x = layers.Bidirectional(layers.LSTM(lstm_units[0], return_sequences=True),
                             name="bilstm1")(x)
    x = layers.Bidirectional(layers.LSTM(lstm_units[1]), name="bilstm2")(x)

    # ---- 全连接分类层 ----
    x = layers.Dense(dense_units, activation="relu", name="dense1")(x)
    if dropout:
        x = layers.Dropout(dropout, name="dropout")(x)
    outputs = layers.Dense(num_classes, activation="softmax", name="output")(x)

    model = models.Model(inputs, outputs, name="cnn_bilstm")
    return model


def compile_model(model, learning_rate=config.LEARNING_RATE):
    """编译模型：Adam + 稀疏交叉熵 + 准确率。"""
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def build_and_compile(**kwargs):
    model = build_cnn_bilstm(**kwargs)
    compile_model(model, learning_rate=kwargs.get("learning_rate", config.LEARNING_RATE))
    return model


def add_channel(X):
    """把 (N, T, F) 扩展为 (N, T, F, 1)，满足 Conv2D 输入。"""
    return X[..., None]
