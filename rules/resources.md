# Resources & Economy

## Resource Types

### Primary Resources
- **Oil**: Currently unused, placeholder for future features
- **Steel**: Currently unused, placeholder for future features
- **Wood**: Produced by Lumber Camps, transported by trucks
- **BMATS**: Basic Materials, currency for building and truck construction

### Production Rates
- **Lumber Camps**: 0.2 wood/sec per tree within 5-cell radius
- **Refineries**: 0.2 bmats/sec per stone pile within 5-cell radius
- **Road Connection Required**: Facilities must be connected to base by roads to produce

## Building Costs

### Infrastructure
- **Road**: 1 BMAT per cell
- **Lumber Camp**: Free (no cost yet)
- **Refinery**: Free (no cost yet)

### Truck Fleet
- **1st Additional Truck**: 10 BMATS
- **2nd Additional Truck**: 25 BMATS (10 + 15)
- **3rd Additional Truck**: 40 BMATS (10 + 15 + 15)
- **4th Additional Truck**: 55 BMATS (10 + 15 + 15 + 15)
- **Formula**: 10 + (15 × trucks_built)

## Resource Flow

### Production Chain
1. **Trees** → Lumber Camp → **Wood**
2. **Stone Piles** → Refinery → **BMATS**

### Transportation
- **Batch Size**: 5 units per truck load
- **Truck Speed**: 1.2 grid cells per second
- **Automated**: Trucks automatically load/unload at facilities
- **Repeat Mode**: Trucks can be set to continuously repeat routes

### Storage
- **Base Inventory**: Unlimited storage for delivered resources
- **Facility Storage**: Accumulates until trucks collect
- **Truck Cargo**: Limited to 20 units capacity
