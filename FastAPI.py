import math
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

app = FastAPI(
    title="Airfare Dataset API",
    description="API to serve and filter Yogesh's cleaned airfare dataset for web frontend.",
    version="1.0.0"
)

# React / Frontend se requests allow karne ke liye CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Production me apne frontend URL se replace karein
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dataset load karein
DATA_PATH = r"C:\Users\Yogesh kumar\Downloads\Freshly cleaned dset Yogesh.xlsx"
print("Loading dataset...")
df = pd.read_excel(DATA_PATH)

# Handling NaNs for JSON compatibility
df = df.fillna("")
print(f"Dataset loaded successfully with {len(df)} rows.")


@app.get("/")
def home():
    return {
        "message": "Airfare Dataset API is live!",
        "total_records": len(df),
        "available_endpoints": [
            "/api/v1/flights",
            "/api/v1/routes",
            "/api/v1/airlines",
            "/api/v1/analytics/route-trends"
        ]
    }


# 1. Paginated & Filtered Flights Endpoint
@app.get("/api/v1/flights")
def get_flights(
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    airline: Optional[str] = Query(None, description="Filter by Airline (e.g. SpiceJet, AirAsia)"),
    origin: Optional[str] = Query(None, alias="from", description="Origin city (e.g. Delhi)"),
    destination: Optional[str] = Query(None, alias="to", description="Destination city (e.g. Mumbai)"),
    class_category: Optional[str] = Query(None, description="Economy or Business"),
    max_price: Optional[float] = Query(None, description="Filter flights below or equal to max price")
):
    filtered_df = df.copy()

    if airline:
        filtered_df = filtered_df[filtered_df['airline'].str.casefold() == airline.casefold()]
    if origin:
        filtered_df = filtered_df[filtered_df['from'].str.casefold() == origin.casefold()]
    if destination:
        filtered_df = filtered_df[filtered_df['to'].str.casefold() == destination.casefold()]
    if class_category:
        filtered_df = filtered_df[filtered_df['class_category'].str.casefold() == class_category.casefold()]
    if max_price is not None:
        filtered_df = filtered_df[filtered_df['price'] <= max_price]

    total_records = len(filtered_df)
    total_pages = math.ceil(total_records / limit) if total_records > 0 else 1

    start_idx = (page - 1) * limit
    end_idx = start_idx + limit
    page_data = filtered_df.iloc[start_idx:end_idx].to_dict(orient="records")

    return {
        "pagination": {
            "current_page": page,
            "limit": limit,
            "total_records": total_records,
            "total_pages": total_pages
        },
        "data": page_data
    }


# 2. Get Unique Dropdown Options (Routes, Airlines, Cities)
@app.get("/api/v1/meta-options")
def get_meta_options():
    return {
        "airlines": sorted(df['airline'].dropna().unique().tolist()),
        "origins": sorted(df['from'].dropna().unique().tolist()),
        "destinations": sorted(df['to'].dropna().unique().tolist()),
        "class_categories": sorted(df['class_category'].dropna().unique().tolist()),
        "routes": sorted(df['route'].dropna().unique().tolist())
    }


# 3. Aggregated Price Trends for Frontend Dashboard Charts
@app.get("/api/v1/analytics/route-trends")
def get_route_analytics(route: str = Query("Delhi-Mumbai", description="Route like 'Delhi-Mumbai'")):
    route_df = df[df['route'].str.casefold() == route.casefold()]

    if route_df.empty:
        raise HTTPException(status_code=404, detail="Route not found")

    # Monthly Average Price Breakdown
    monthly_stats = route_df.groupby(['year', 'month_category'])['price'].agg(['mean', 'min', 'max', 'count']).reset_index()
    monthly_stats['mean'] = monthly_stats['mean'].round(2)

    # Airline Comparison on this Route
    airline_stats = route_df.groupby('airline')['price'].agg(['mean', 'count']).reset_index()
    airline_stats['mean'] = airline_stats['mean'].round(2)

    return {
        "route": route,
        "total_flights": len(route_df),
        "avg_price": round(float(route_df['price'].mean()), 2),
        "monthly_trends": monthly_stats.to_dict(orient="records"),
        "airline_breakdown": airline_stats.to_dict(orient="records")
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
