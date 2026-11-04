"""校验源码包并检查随机输入的前向/反向传播；不训练正式模型、不需要数据或权重。"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hash-only', action='store_true')
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'MANIFEST.json').read_text(encoding='utf-8'))
    for item in manifest['files']:
        path = ROOT / item['path']
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != item['sha256']:
            raise ValueError(f"File hash mismatch: {item['path']}")
    sources = list(ROOT.rglob('*.py'))
    for path in sources:
        ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    result = dict(file_hashes_verified=len(manifest['files']), python_files_parsed=len(sources),
                  original_workspace_required=False, models=[])
    if not args.hash_only:
        import torch
        from ndp_tcn.model import build_model, ResidualConfig, TiNpuConfig, TiNpuFullConvConfig
        torch.set_num_threads(2)
        torch.manual_seed(2026)
        for backend, config in [('original', ResidualConfig(variant='baseline')),
                                ('ti_npu', TiNpuConfig()),
                                ('ti_npu_fullconv', TiNpuFullConvConfig())]:
            model = build_model(config, backend=backend)
            for module in model.modules():
                file = getattr(sys.modules.get(type(module).__module__), '__file__', None)
                if file and ('ndp_tcn' in str(file) or 'ModernTCN-main' in str(file)):
                    Path(file).resolve().relative_to(ROOT)
            x = torch.randn(2, 8, 9)
            model.train()
            output = model(x)
            assert output.shape == (2, 1) and torch.isfinite(output).all()
            output.square().mean().backward()
            grads = [p.grad for p in model.parameters() if p.grad is not None]
            assert grads and all(torch.isfinite(g).all() for g in grads)
            model.eval()
            with torch.no_grad():
                prediction = model(x)
                assert prediction.shape == (2, 1) and torch.isfinite(prediction).all()
            result['models'].append(dict(backend=backend, parameters=sum(p.numel() for p in model.parameters()),
                                        input_shape=list(x.shape), output_shape=list(prediction.shape),
                                        forward_backward_finite=True))
        result['torch_version'] = torch.__version__
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
