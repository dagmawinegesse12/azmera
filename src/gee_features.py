"""
Azmera — Google Earth Engine Features
Pulls NDVI, soil moisture, and CHIRPS rainfall for Ethiopian regions.
"""

import ee
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import json
import os

REGION_GEOMETRIES = {
    "Tigray":            {"lat": 14.0, "lon": 38.5, "buffer": 150000},
    "Afar":              {"lat": 11.8, "lon": 40.9, "buffer": 180000},
    "Amhara":            {"lat": 11.3, "lon": 37.8, "buffer": 200000},
    "Oromia":            {"lat":  7.5, "lon": 39.0, "buffer": 300000},
    "Somali":            {"lat":  6.5, "lon": 44.0, "buffer": 250000},
    "Benishangul-Gumz":  {"lat": 11.0, "lon": 35.5, "buffer": 150000},
    "SNNPR":             {"lat":  6.5, "lon": 37.5, "buffer": 200000},
    "Gambela":           {"lat":  8.0, "lon": 34.5, "buffer": 100000},
    "Harari":            {"lat":  9.3, "lon": 42.1, "buffer":  30000},
    "Dire Dawa":         {"lat":  9.6, "lon": 41.9, "buffer":  25000},
    "Addis Ababa":       {"lat":  9.0, "lon": 38.7, "buffer":  25000},
    "Sidama":            {"lat":  6.8, "lon": 38.4, "buffer":  80000},
    "Southwest Ethiopia":{"lat":  7.0, "lon": 35.8, "buffer":  80000},
}

def init_gee():
    try:
        try:
            print(f"GEE debug — available secret keys: {list(st.secrets.keys())}")
            key_dict = dict(st.secrets["gee"])
            key_str = json.dumps(key_dict)  # convert dict → JSON string
            service_account = key_dict["client_email"]
            credentials = ee.ServiceAccountCredentials(
                service_account, key_data=key_str
            )
            ee.Initialize(credentials)
            print("GEE init success!")
            return True
        except KeyError as e:
            print(f"GEE secret KeyError: {e}")
        except Exception as e:
            print(f"GEE secret error: {e}")

        # Fall back to local
        key_path = os.path.expanduser("~/secrets/azmera-gee-key.json")
        if os.path.exists(key_path):
            with open(key_path) as f:
                key_str = f.read()
            key_dict = json.loads(key_str)
            service_account = key_dict["client_email"]
            credentials = ee.ServiceAccountCredentials(service_account, key_data=key_str)
            ee.Initialize(credentials)
            return True

        print("GEE init failed: no credentials found")
        return False

    except Exception as e:
        print(f"GEE init failed: {e}")
        return False
    
def get_region_geometry(region_name):
    r = REGION_GEOMETRIES.get(region_name)
    if not r:
        return None
    point = ee.Geometry.Point([r["lon"], r["lat"]])
    return point.buffer(r["buffer"])


def get_ndvi(region_name, months_back=3):
    try:
        geometry = get_region_geometry(region_name)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        collection = (
            ee.ImageCollection("MODIS/061/MOD13A3")
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filterBounds(geometry)
            .select("NDVI")
        )
        current_ndvi = collection.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=1000, maxPixels=1e9
        ).getInfo()
        ndvi_raw = current_ndvi.get("NDVI", None)
        if ndvi_raw is None:
            return {"status": "unavailable", "mean_ndvi": None, "ndvi_anomaly": None}
        ndvi_scaled = ndvi_raw * 0.0001
        baseline_collection = (
            ee.ImageCollection("MODIS/061/MOD13A3")
            .filter(ee.Filter.calendarRange(start_date.month, end_date.month, "month"))
            .filter(ee.Filter.date("2000-01-01", "2020-12-31"))
            .filterBounds(geometry)
            .select("NDVI")
        )
        baseline_raw = baseline_collection.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=1000, maxPixels=1e9
        ).getInfo().get("NDVI", None)
        baseline_scaled = baseline_raw * 0.0001 if baseline_raw else None
        anomaly = None
        if baseline_scaled and baseline_scaled > 0:
            anomaly = ((ndvi_scaled - baseline_scaled) / baseline_scaled) * 100
        if anomaly is None: status = "unknown"
        elif anomaly < -20: status = "severely_stressed"
        elif anomaly < -10: status = "stressed"
        elif anomaly < 5:   status = "normal"
        else:               status = "above_normal"
        return {
            "status": status,
            "mean_ndvi": round(ndvi_scaled, 3),
            "baseline_ndvi": round(baseline_scaled, 3) if baseline_scaled else None,
            "ndvi_anomaly": round(anomaly, 1) if anomaly else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "mean_ndvi": None, "ndvi_anomaly": None}


def get_chirps_rainfall(region_name, months_back=3):
    try:
        geometry = get_region_geometry(region_name)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        collection = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filterBounds(geometry)
        )
        # Use mean daily rainfall for fair comparison
        current_mean = collection.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=5000, maxPixels=1e9
        ).getInfo().get("precipitation", None)
        total_mm = current_mean * months_back * 30 if current_mean else None
        if total_mm is None:
            return {"status": "unavailable", "total_mm": None, "anomaly_pct": None}
        baseline_daily = (
            ee.ImageCollection("UCSB-CHG/CHIRPS/DAILY")
            .filter(ee.Filter.calendarRange(start_date.month, end_date.month, "month"))
            .filter(ee.Filter.date("1981-01-01", "2020-12-31"))
            .filterBounds(geometry)
            .mean()
            .reduceRegion(reducer=ee.Reducer.mean(), geometry=geometry, scale=5000, maxPixels=1e9)
            .getInfo().get("precipitation", None)
        )
        baseline_mm = baseline_daily * months_back * 30 if baseline_daily else None
        anomaly_pct = None
        if baseline_mm and baseline_mm > 0:
            anomaly_pct = ((total_mm - baseline_mm) / baseline_mm) * 100
        if anomaly_pct is None:   status = "unknown"
        elif anomaly_pct < -30:   status = "severe_deficit"
        elif anomaly_pct < -15:   status = "below_normal"
        elif anomaly_pct < 15:    status = "normal"
        else:                     status = "above_normal"
        return {
            "status": status,
            "total_mm": round(total_mm, 1),
            "baseline_mm": round(baseline_mm, 1) if baseline_mm else None,
            "anomaly_pct": round(anomaly_pct, 1) if anomaly_pct else None,
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "total_mm": None, "anomaly_pct": None}


def get_soil_moisture(region_name, months_back=1):
    try:
        geometry = get_region_geometry(region_name)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        collection = (
            ee.ImageCollection("NASA/SMAP/SPL4SMGP/008")
            .filterDate(start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"))
            .filterBounds(geometry)
            .select("sm_surface_wetness")
        )
        sm_value = collection.mean().reduceRegion(
            reducer=ee.Reducer.mean(), geometry=geometry, scale=10000, maxPixels=1e9
        ).getInfo().get("sm_surface_wetness", None)
        if sm_value is None:
            return {"status": "unavailable", "mean_sm": None}
        if sm_value < 5:    status = "very_dry"
        elif sm_value < 15: status = "dry"
        elif sm_value < 30: status = "normal"
        elif sm_value < 45: status = "wet"
        else:               status = "very_wet"
        return {"status": status, "mean_sm": round(sm_value, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e), "mean_sm": None}


def get_all_gee_features(region_name):
    if not init_gee():
        return {"available": False, "error": "GEE initialization failed"}
    return {
        "available": True,
        "region": region_name,
        "retrieved_at": datetime.now().strftime("%Y-%m-%d %H:%M UTC"),
        "ndvi": get_ndvi(region_name, months_back=3),
        "chirps": get_chirps_rainfall(region_name, months_back=3),
        "soil_moisture": get_soil_moisture(region_name, months_back=1),
    }


def render_gee_panel(region_name):
    st.markdown("---")
    st.markdown("### 🛰️ Live Satellite Indicators")
    st.caption(f"Google Earth Engine data for {region_name.title()} — updated daily")
    with st.spinner("Fetching satellite data..."):
        data = get_all_gee_features(region_name)
    if not data.get("available"):
        st.warning("Satellite data temporarily unavailable.")
        return
    col1, col2, col3 = st.columns(3)
    with col1:
        ndvi = data["ndvi"]
        ndvi_val = ndvi.get("mean_ndvi")
        anomaly = ndvi.get("ndvi_anomaly")
        icon, label = {"severely_stressed": ("🔴","Severely Stressed"), "stressed": ("🟠","Stressed"), "normal": ("🟢","Normal"), "above_normal": ("💚","Above Normal")}.get(ndvi.get("status","unknown"), ("⚪","Unknown"))
        st.metric(label=f"{icon} Vegetation Health (NDVI)", value=f"{ndvi_val:.3f}" if ndvi_val else "N/A", delta=f"{anomaly:+.1f}% vs baseline" if anomaly else None, delta_color="normal")
        st.caption(f"MODIS Terra · 3-month mean · {label}")
    with col2:
        chirps = data["chirps"]
        total_mm = chirps.get("total_mm")
        anomaly = chirps.get("anomaly_pct")
        icon, label = {"severe_deficit": ("🔴","Severe Deficit"), "below_normal": ("🟠","Below Normal"), "normal": ("🟢","Normal"), "above_normal": ("💙","Above Normal")}.get(chirps.get("status","unknown"), ("⚪","Unknown"))
        st.metric(label=f"{icon} Rainfall (CHIRPS)", value=f"{total_mm:.0f} mm" if total_mm else "N/A", delta=f"{anomaly:+.1f}% vs baseline" if anomaly else None, delta_color="normal")
        st.caption(f"CHIRPS 5km · 3-month total · {label}")
    with col3:
        soil = data["soil_moisture"]
        sm_val = soil.get("mean_sm")
        icon, label = {"very_dry": ("🔴","Very Dry"), "dry": ("🟠","Dry"), "normal": ("🟢","Normal"), "wet": ("💙","Wet"), "very_wet": ("🌊","Very Wet")}.get(soil.get("status","unknown"), ("⚪","Unknown"))
        st.metric(label=f"{icon} Soil Moisture (SMAP)", value=f"{sm_val:.1f} mm" if sm_val else "N/A")
        st.caption(f"NASA SMAP 10km · 30-day mean · {label}")
    st.caption(f"🛰️ Data retrieved: {data.get('retrieved_at', 'unknown')}")
