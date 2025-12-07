from typing import List, Tuple, Dict, Any, Optional

class HeightmapCell:
    def __init__(self, height: int, walkable: int) -> None:
        self.height: int = height
        self.walkable: int = walkable

    def is_walkable(self) -> bool:
        return self.walkable < 4


class Heightmap:
    def __init__(self) -> None:
        self.left_offset: int = 0
        self.top_offset: int = 0
        self.cells: List[List[HeightmapCell]] = []

    def load_from_properties(self, properties: Dict[str, Any]) -> None:
        """Load heightmap from TMX room properties."""
        # Get dimensions and offsets from properties
        width: int = int(properties.get('hmwidth', 0))
        height: int = int(properties.get('hmheight', 0))
        self.left_offset = int(properties.get('hmleft', 0))
        self.top_offset = int(properties.get('hmtop', 0))
        
        print(self.left_offset)
        print(self.top_offset)

        # Get the heightmap data string
        heightmap_str: str = properties.get('heightmap', '')
        
        # Split by newlines and commas to get all hex values
        heightmap_str = heightmap_str.replace('&#10;', '\n')
        lines: List[str] = [line.strip() for line in heightmap_str.split('\n') if line.strip()]
        
        # Parse the hex values (format: "0x4000" or "4000")
        hex_values: List[str] = []
        for line in lines:
            # Split by comma and strip whitespace
            values = [v.strip() for v in line.split(',') if v.strip()]
            hex_values.extend(values)
        
        # Convert hex values to cells
        self.cells = []
        for y in range(height):
            row: List[HeightmapCell] = []
            for x in range(width):
                index: int = y * width + x
                if index < len(hex_values):
                    # Remove "0x" prefix if present
                    hex_str: str = hex_values[index].replace('0x', '').replace('0X', '')
                    
                    # Format: each hex value is 4 digits like "4000"
                    # Index 0 = walkable status (single hex digit)
                    # Index 1 = height (single hex digit)
                    # Indices 2-3 = other status (ignored for now)
                    walkable: int = int(hex_str[0], 16)
                    height_val: int = int(hex_str[1], 16)
                    
                    row.append(HeightmapCell(height=height_val, walkable=walkable))
                else:
                    # Default empty cell if data is missing
                    row.append(HeightmapCell(height=0, walkable=4))
            self.cells.append(row)
        
        print(f"Loaded heightmap: {width}x{height}, offset=({self.left_offset},{self.top_offset})")

    def get_width(self) -> int:
        return len(self.cells[0]) if self.cells else 0

    def get_height(self) -> int:
        return len(self.cells)

    def get_cell(self, x: int, y: int) -> Optional[HeightmapCell]:
        if 0 <= y < len(self.cells) and 0 <= x < len(self.cells[0]):
            return self.cells[y][x]
        return None