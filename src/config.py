import os
from typing import Dict, Any, List, Optional

class Config:
    def __init__(self, filepath: str = "config.yml"):
        # fallback to absolute path or check parent directories if needed
        if not os.path.exists(filepath):

            possible_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), filepath)
            if os.path.exists(possible_path):
                filepath = possible_path

        self.filepath = filepath
        self.data: Dict[str, Any] = {}
        self.load()

    def load(self):
        if os.path.exists(self.filepath):
            with open(self.filepath, "r", encoding="utf-8") as f:
                content = f.read()
                try:
                    import yaml
                    self.data = yaml.safe_load(content) or {}
                except ImportError:
                    self.data = self._parse_simple_yaml(content)
        else:
            print(f"Config file not found at {self.filepath}, using defaults")
            self.data = {}

    def _parse_simple_yaml(self, content: str) -> Dict[str, Any]:
        """YAML parser extarnal packages."""
        data = {"filters": {}, "sources": []}
        current_section = None
        
        for line in content.splitlines():
            # remove comments and whitespace
            line = line.split("#")[0].strip()
            if not line:
                continue
                
            if line.endswith(":"):
                current_section = line[:-1].strip()
                continue
                
            if line.startswith("-") and current_section == "sources":
                val = line[1:].strip().strip('"').strip("'")
                data["sources"].append(val)
                continue
                
            if ":" in line:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                
                # convert 
                if val.lower() == "true":
                    val_parsed = True
                elif val.lower() == "false":
                    val_parsed = False
                else:
                    try:
                        if "." in val:
                            val_parsed = float(val)
                        else:
                            val_parsed = int(val)
                    except ValueError:
                        val_parsed = val
                        
                if current_section == "filters":
                    data["filters"][key] = val_parsed
                else:
                    data[key] = val_parsed
                    
        return data

    @property
    def filters(self) -> Dict[str, Any]:
        return self.data.get("filters", {})

    @property
    def sources(self) -> List[str]:
        return self.data.get("sources", ["gesiba", "sozialbau", "wohnen", "oevw", "siedlungsunion", "familienwohnbau", "oesw", "egw"])

    @property
    def max_price(self) -> Optional[float]:
        val = self.filters.get("max_price")
        return float(val) if val is not None else None

    @property
    def min_size_sqm(self) -> Optional[float]:
        val = self.filters.get("min_size_sqm")
        return float(val) if val is not None else None

    @property
    def min_rooms(self) -> Optional[int]:
        val = self.filters.get("min_rooms")
        return int(val) if val is not None else None

    @property
    def location_contains(self) -> Optional[str]:
        return self.filters.get("location_contains")

    @property
    def immediate_only(self) -> bool:
        return bool(self.filters.get("immediate_only", True))

