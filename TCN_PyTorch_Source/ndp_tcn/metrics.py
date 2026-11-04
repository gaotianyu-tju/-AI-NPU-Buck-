"""在物理单位 V/s 下评价，不使用加权训练损失冒充预测误差。"""
import numpy as np
import torch


def predict_array(model, scalers, windows, batch_size, device):
    model.eval()
    predictions = []
    with torch.inference_mode():
        for start in range(0, len(windows), batch_size):
            normalized = scalers.transform_x(windows[start:start+batch_size])
            batch = torch.as_tensor(normalized, dtype=torch.float32, device=device)
            pred = model(batch).cpu().numpy()
            predictions.append(scalers.inverse_y(pred))
    if not predictions:
        raise ValueError("Cannot predict an empty input.")
    result = np.concatenate(predictions).astype(np.float64)
    if result.shape != (len(windows), 1) or not np.isfinite(result).all():
        raise ValueError("Model returned an invalid residual prediction.")
    return result


def evaluate_model(model, cases, scalers, batch_size, device):
    records, sum_sq, sum_abs, zero_sq, count = [], 0.0, 0.0, 0.0, 0
    for case in cases:
        pred = predict_array(model, scalers, case.X, batch_size, device)
        target = case.y.astype(np.float64)
        err = pred-target
        n = len(target)
        records.append({
            "file": str(case.path), "case_id": int(case.metadata["case_id"]),
            "sample_count": n,
            "rmse_V_per_s": float(np.sqrt(np.mean(err**2))),
            "mae_V_per_s": float(np.mean(np.abs(err))),
            "max_abs_error_V_per_s": float(np.max(np.abs(err))),
            "zero_residual_rmse_V_per_s": float(np.sqrt(np.mean(target**2))),
        })
        sum_sq += float(np.sum(err**2))
        sum_abs += float(np.sum(np.abs(err)))
        zero_sq += float(np.sum(target**2))
        count += n
    if not count:
        raise ValueError("Evaluation requires at least one case.")
    return {
        "sample_count": count, "case_count": len(records),
        "rmse_V_per_s": float(np.sqrt(sum_sq/count)),
        "mae_V_per_s": sum_abs/count,
        "macro_rmse_V_per_s": float(np.mean([r["rmse_V_per_s"] for r in records])),
        "zero_residual_rmse_V_per_s": float(np.sqrt(zero_sq/count)),
        "zero_residual_macro_rmse_V_per_s": float(np.mean([r["zero_residual_rmse_V_per_s"] for r in records])),
        "selection_metric": "macro_rmse_V_per_s (arithmetic mean of per-case RMSE)",
        "cases": records,
    }
