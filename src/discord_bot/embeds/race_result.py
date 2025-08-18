"""
Helper module for building race result embeds that are identical to what the poller posts.
This ensures consistency between automated poller messages and manual /lastrace command responses.
"""

from __future__ import annotations
import discord
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    # adjust to the real location of the dataclass; this avoids runtime import
    from iracing.service import FinishRecord


def build_race_result_embed(record: FinishRecord) -> discord.Embed:
    """
    Build a Discord embed for a race result with identical formatting to the poller.
    
    This function replicates the exact same logic used in IR2DISBot.post_finish_embed()
    to ensure byte-for-byte identical output between automated messages and command responses.
    """
    # Determine color based on finish position
    if record.finish_pos <= 3:
        color = discord.Color.green()
    elif record.finish_pos <= 10:
        color = discord.Color.orange()
    else:
        color = discord.Color.red()
    
    # Build title - include class position if available
    title_parts = [f"🏁 {record.display_name} — P{record.finish_pos}"]
    if record.finish_pos_in_class:
        title_parts.append(f"(Class P{record.finish_pos_in_class})")
    title = " ".join(title_parts)
    
    # Build description with all the details
    description_lines = [
        f"**Series:** {record.series_name} • **Track:** {record.track_name} • **Car:** {record.car_name}",
        f"**Field:** {record.field_size} • **Laps:** {record.laps} • **Inc:** {record.incidents} • **SOF:** {record.sof or '—'}"
    ]
    
    if record.best_lap_time_s:
        description_lines.append(f"**Best:** {record.best_lap_time_s:.3f}s")
    
    description_lines.append("Official: ✅" if record.official else "Official: ❌")
    
    # Create the embed
    embed = discord.Embed(
        title=title,
        description="\n".join(description_lines),
        color=color
    )
    
    # Add footer with subsession ID and timestamp
    embed.set_footer(text=f"Subsession {record.subsession_id} • {record.start_time_utc}")
    
    return embed
