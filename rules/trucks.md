# Truck System & Logistics

## Truck Management

### Selection & Control
- **Number Keys**: Press 1-9 to select trucks (1 = first truck, 2 = second truck, etc.)
- **Visual Indicators**: Selected truck shows blue circle with white border
- **Info Panel**: Right side shows detailed truck information when selected

### Truck Properties
- **Speed**: 1.2 grid cells per second
- **Cargo Capacity**: 20 units maximum
- **Batch Size**: 5 units per load/unload operation
- **Unique Colors**: Each truck has distinct marker and path colors

## Logistics System

### Route Assignment
1. **Click Base**: Shows available trucks
2. **Select Truck**: Choose from available trucks
3. **Click Source**: Select lumber camp or refinery
4. **Select Resource**: Choose wood or BMATS
5. **Confirm**: Truck begins automated route

### Route Types
- **To Source**: Truck drives to resource facility
- **Loading**: Truck loads 5 units from facility
- **To Destination**: Truck drives to main base
- **Unloading**: Truck delivers resources to base inventory

### Automation Features
- **Repeat Mode**: Trucks can continuously repeat assigned routes
- **Pathfinding**: Automatic route calculation using road network
- **Building Entry**: Trucks drive directly into facilities for loading

## Visual Feedback

### Truck Display
- **Sprite System**: High-quality truck images with smooth scaling
- **Rotation**: Trucks automatically face movement direction
- **Path Visualization**: Colored circles show planned route
- **Position Markers**: Real-time truck location indicators

### Status Information
- **Current State**: Idle, Moving, Loading, Unloading
- **Cargo Status**: Type and amount of carried resources
- **Destination**: Clear indication of where truck is heading
- **Path Length**: Number of cells to destination

## Fleet Expansion

### Building New Trucks
- **Base Button**: Green "+" button in top-right corner of base
- **Cost Scaling**: Each additional truck costs more than the last
- **Immediate Use**: New trucks are immediately available for assignment
- **Unique Identity**: Each truck gets distinct visual appearance
