"""
Nearest police stations & hospitals from CSV datasets (haversine distance).
"""

import logging
import math
import os
from typing import Any, Dict, List, Optional

import pandas as pd

from utils.sri_lanka_geo import DISTRICT_COORDS

logger = logging.getLogger(__name__)

DATASETS_DIR = os.path.join(os.path.dirname(__file__), "..", "datasets")

_police_df: Optional[pd.DataFrame] = None
_hospitals_df: Optional[pd.DataFrame] = None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlamb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlamb / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _load_csv(name: str) -> pd.DataFrame:
    path = os.path.join(DATASETS_DIR, name)
    if not os.path.exists(path):
        logger.warning("Facilities CSV missing: %s", path)
        return pd.DataFrame()
    df = pd.read_csv(path)
    df.columns = [str(c).strip() for c in df.columns]
    for col in ("latitude", "longitude"):
        if col not in df.columns:
            logger.warning("CSV %s missing column %s", name, col)
            return pd.DataFrame()
    return df


def load_facility_tables() -> None:
    """Load police_stations.csv & hospitals.csv once."""
    global _police_df, _hospitals_df
    _police_df = _load_csv("police_stations.csv")
    _hospitals_df = _load_csv("hospitals.csv")
    logger.info(
        "Facilities loaded: police=%s hospitals=%s",
        len(_police_df),
        len(_hospitals_df),
    )


def _safe_float(v: Any) -> Optional[float]:
    try:
        x = float(v)
    except (TypeError, ValueError):
        return None
    if math.isnan(x) or math.isinf(x):
        return None
    return x


def _nearest_from_df(df: pd.DataFrame, lat: float, lon: float, n: int = 3) -> List[Dict[str, Any]]:
    """Return JSON-safe dicts (native Python floats/str — no numpy/pandas scalars)."""
    if df is None or df.empty:
        return []
    rows = []
    for _, row in df.iterrows():
        plat = _safe_float(row.get("latitude"))
        plon = _safe_float(row.get("longitude"))
        if plat is None or plon is None:
            continue
        d = _haversine_km(lat, lon, plat, plon)
        if math.isnan(d) or math.isinf(d):
            continue
        phone = row.get("phone", "")
        if pd.isna(phone):
            phone = ""
        rows.append(
            {
                "name": str(row.get("name", "") or ""),
                "district": str(row.get("district", "") or ""),
                "latitude": float(plat),
                "longitude": float(plon),
                "distance_km": float(round(float(d), 2)),
                "phone": str(phone),
            }
        )
    rows.sort(key=lambda x: x["distance_km"])
    return rows[:n]


def nearest_facilities(lat: float, lon: float, police_n: int = 3, hospital_n: int = 3) -> Dict[str, Any]:
    """Return nearest police stations and hospitals from reference point."""
    if _police_df is None or _hospitals_df is None:
        load_facility_tables()
    # Never use `df or pd.DataFrame()` — pandas forbids bool(DataFrame).
    police = _police_df if _police_df is not None else pd.DataFrame()
    hospitals = _hospitals_df if _hospitals_df is not None else pd.DataFrame()
    return {
        "nearest_police": _nearest_from_df(police, lat, lon, police_n),
        "nearest_hospitals": _nearest_from_df(hospitals, lat, lon, hospital_n),
    }
