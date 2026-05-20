"""cloud-metrics 路由注册顺序（静态路径须在 {metric_id} 之前）"""


def _cloud_metric_paths():
    from main import app

    paths = []
    for route in app.routes:
        path = getattr(route, "path", None)
        if path and "/cloud-metrics" in path:
            paths.append(path)
    return paths


def test_cloud_metrics_map_before_metric_id():
    paths = _cloud_metric_paths()
    map_idx = next(i for i, p in enumerate(paths) if p.endswith("/cloud-metrics/map"))
    metric_id_idx = next(i for i, p in enumerate(paths) if "{metric_id}" in p)
    assert map_idx < metric_id_idx
