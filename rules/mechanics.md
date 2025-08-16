# Game Mechanics

## Core Systems

### Building System
- **Roads**: Connect facilities to base, cost 1 BMAT each
- **Lumber Camps**: Produce wood from nearby trees (0.2 wood/sec per tree)
- **Refineries**: Produce BMATS from nearby stone piles (0.2 bmats/sec per stone)
- **Base**: 2x2 grid, starting point for all operations

### Resource Production
- **Connected Production**: Facilities only produce when connected to base by roads
- **Tree Density**: Reduced to 1/2 previous amount for balance
- **Stone Piles**: 1/4 of tree amount, 50% larger than trees
- **Production Radius**: 5 cells for both lumber camps and refineries

### Obstacle System
- **Trees**: Green circular obstacles, prevent building
- **Stones**: Grey irregular obstacles, prevent building
- **Roads**: Can be built on empty cells, refund 1 BMAT when bulldozed

## Game Flow

### Starting Setup
- Base spawns randomly in viewport
- 2 starting trucks available
- 10 BMATS starting resources
- Trees and stones scattered around map

### Progression
- Build roads to connect facilities
- Place production buildings near resources
- Assign trucks to transport resources
- Expand truck fleet as needed

### Win Conditions
- Currently open-ended sandbox gameplay
- Focus on efficient logistics and resource management
