---
phase: quick-011
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - core/views.py
autonomous: true
---

<objective>
Add fantasy and ninja emoji options to the kid emoji avatar picker.
Expand EMOJI_CHOICES with ~11 new emojis: fantasy characters (wizard, fairy, elf, vampire, genie, dragon, magic wand, crystal ball, swords, castle) and ninja.
</objective>

<tasks>
<task type="auto">
  <name>Task 1: Expand EMOJI_CHOICES with fantasy and ninja emojis</name>
  <files>core/views.py</files>
  <action>Add Fantasy and Ninja categories to EMOJI_CHOICES list</action>
  <done>Kids can now choose from fantasy and ninja emojis in the settings page</done>
</task>
</tasks>
