import pandas as pd
import numpy as np
import torch


def partition(file_path, train_size=0.8):
    data = pd.read_csv(file_path)
    train_length = int(len(data) * train_size)

    # 划分数据
    train_data = data[:train_length]
    val_data = data[train_length:]

    return train_data, val_data


def multiscale_divider(condition):
    # 分割条件向量
    hourly_condition = condition[:, :24]
    daily_condition = condition[:, 24:31]
    weekly_condition = condition[:, 31:83]
    wind_condition = condition[:, 83:]

    return hourly_condition, daily_condition, weekly_condition, wind_condition


def simulate_masked_data(df, column_names, missing_rate=0.1, max_missing_length=24, missing_mode='continuous'):
    """
    模拟缺失数据的掩码，并返回掩码矩阵。

    :param df: 输入数据框
    :param column_names: 需要插补的列名
    :param missing_rate: 缺失数据的比例
    :param max_missing_length: 最大缺失长度（用于连续缺失模式）
    :param missing_mode: 缺失模式，'random' 表示离散随机缺失，'continuous' 表示连续长序列缺失
    :return: 掩码矩阵
        0 代表缺失数据的位置，即数据在这些位置是缺失的。
        1 代表数据存在的位置，即这些位置的数据是有效的。
    """

    df_copy = df.copy()
    num_rows = len(df_copy)
    columns = df_copy[column_names].values

    # 初始化掩码矩阵
    mask = np.ones(columns.shape, dtype=np.float32)

    if missing_mode == 'random':
        # 随机缺失
        num_missing = int(num_rows * missing_rate)
        missing_indices = np.random.choice(num_rows, num_missing, replace=False)
        mask[missing_indices] = 0
    elif missing_mode == 'continuous':
        # 连续长序列缺失
        num_missing = int(num_rows * missing_rate)
        if max_missing_length > num_missing:
            max_missing_length = num_missing
        for column_index in range(columns.shape[1]):
            num_segments = max(int(num_missing / max_missing_length), 1)
            centering = (num_segments == 1)
            for _ in range(num_segments):
                if centering:
                    # Center the segment
                    middle_index = num_rows // 2
                    start_index = max(0, middle_index - max_missing_length // 2)
                    end_index = min(start_index + max_missing_length, num_rows)

                    # Adjust start index to fit within bounds
                    if end_index - start_index < max_missing_length:
                        start_index = max(0, end_index - max_missing_length)

                else:
                    # Randomly select start index
                    start_index = np.random.randint(0, num_rows - max_missing_length + 1)
                    end_index = start_index + max_missing_length

                # Ensure indices are integers
                start_index = int(start_index)
                end_index = int(end_index)

                # Ensure indices are within bounds and do not exceed the number of rows
                start_index = max(0, start_index)
                end_index = min(num_rows, end_index)

                # Apply the mask
                mask[start_index:end_index, column_index] = 0

                # Ensure mask length reaches expected proportion
                if np.sum(mask[:, column_index] == 0) >= num_missing:
                    break
    else:
        raise ValueError("Invalid missing_mode. Choose between 'random' and 'continuous'")

    # 转换掩码矩阵为 tensor
    mask_tensor = torch.tensor(mask, dtype=torch.float32)

    return mask_tensor
