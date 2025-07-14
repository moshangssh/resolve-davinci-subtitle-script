from dataclasses import dataclass, field
from typing import List

@dataclass
class UIModel:
    """
    UIModel 用于存储和管理界面的状态。
    """
    search_text: str = ""
    find_text: str = ""
    filter_type: str = "包含"
    displayed_subtitles: List[dict] = field(default_factory=list)
