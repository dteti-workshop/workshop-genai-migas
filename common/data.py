"""Pemuat data yang dipakai lebih dari satu unit."""
from __future__ import annotations

import pandas as pd

from common.config import DATA


def load_hse(test_frac: float = 0.65, seed: int = 7) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Laporan insiden HSE beserta label acuan, dipisah menjadi data uji dan data pool.

    Data uji hanya dipakai untuk mengukur akurasi. Contoh few-shot dan data dev diambil dari pool,
    sehingga tidak ada data uji yang pernah dilihat saat prompt disusun.
    Pemisahan dilakukan per incident_type (stratified) dengan seed tetap agar hasil antarpeserta sama.
    """
    inc = pd.read_csv(DATA / "raw" / "hse_incidents.csv")
    truth = pd.read_csv(DATA / "eval" / "hse_incidents_truth.csv")
    df = inc.merge(truth, on="incident_id")
    uji = df.groupby("incident_type", group_keys=False).sample(frac=test_frac, random_state=seed)
    pool = df.drop(uji.index)
    return uji.reset_index(drop=True), pool.reset_index(drop=True)
