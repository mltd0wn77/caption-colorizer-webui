"""
FCPXML writer for Final Cut Pro X / Premiere Pro compatibility
Generates FCPXML 1.6 format for caption overlays
"""

from pathlib import Path
from typing import List, Dict
import xml.etree.ElementTree as ET
import xml.dom.minidom as minidom


def write_fcpxml(items: List[Dict], fps: float, out_xml: Path, track_index: int = 2):
    """
    Generate an FCPXML file for importing caption images into Final Cut Pro X or Premiere Pro.
    
    Args:
        items: List of dicts with 'file', 'start_frame', 'end_frame', 'offset_x', 'offset_y'
        fps: Frame rate of the video
        out_xml: Output path for the FCPXML file
        track_index: Track index for placing captions (default: 2)
    """
    # Calculate frame duration
    frame_duration = 1.0 / fps
    
    # Create FCPXML root with proper namespace
    fcpxml = ET.Element('fcpxml', version='1.6')
    
    # Add resources section
    resources = ET.SubElement(fcpxml, 'resources')
    
    # Add format resource (standard HD format)
    format_elem = ET.SubElement(resources, 'format', {
        'id': 'r1',
        'name': 'FFVideoFormat1080p30',
        'frameDuration': f'{int(1000/fps)}/1000s',
        'width': '1920',
        'height': '1080'
    })
    
    # Add media resources for each caption image
    for idx, item in enumerate(items):
        asset = ET.SubElement(resources, 'asset', {
            'id': f'r{idx+2}',
            'name': item['file'],
            'src': f'file://./{item["file"]}',
            'hasVideo': '1',
            'format': 'r1'
        })
    
    # Create library and event structure
    library = ET.SubElement(fcpxml, 'library')
    event = ET.SubElement(library, 'event', {'name': 'Caption Import'})
    
    # Create project with sequence
    project = ET.SubElement(event, 'project', {'name': 'Caption Sequence'})
    
    # Calculate total duration
    if items:
        total_frames = max(item['end_frame'] for item in items)
        total_duration = total_frames * frame_duration
    else:
        total_duration = 0
    
    # Create sequence
    sequence = ET.SubElement(project, 'sequence', {
        'format': 'r1',
        'duration': f'{total_duration:.3f}s'
    })
    
    # Create spine (main timeline container)
    spine = ET.SubElement(sequence, 'spine')
    
    # Add a gap element to establish timeline duration
    if total_duration > 0:
        gap = ET.SubElement(spine, 'gap', {
            'offset': '0s',
            'duration': f'{total_duration:.3f}s'
        })
    
    # Add video track for captions
    for idx, item in enumerate(items):
        start_time = item['start_frame'] * frame_duration
        duration = (item['end_frame'] - item['start_frame']) * frame_duration
        
        # Create clip reference
        clip = ET.SubElement(spine, 'video', {
            'name': item['file'],
            'offset': f'{start_time:.3f}s',
            'ref': f'r{idx+2}',
            'duration': f'{duration:.3f}s'
        })
        
        # Add transform if offsets are specified
        if item.get('offset_x', 0) != 0 or item.get('offset_y', 0) != 0:
            transform = ET.SubElement(clip, 'transform', {
                'position': f"{item.get('offset_x', 0)} {-item.get('offset_y', 0)}"
            })
    
    # Convert to string and format nicely
    xml_str = ET.tostring(fcpxml, encoding='unicode')
    
    # Pretty print the XML
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ')
    
    # Remove extra blank lines
    lines = [line for line in pretty_xml.split('\n') if line.strip()]
    pretty_xml = '\n'.join(lines)
    
    # Write to file
    with open(out_xml, 'w', encoding='utf-8') as f:
        f.write(pretty_xml)
    
    return out_xml


# Alternative simpler implementation if the above doesn't work
def write_simple_fcpxml(items: List[Dict], fps: float, out_xml: Path, track_index: int = 2):
    """
    Simplified FCPXML writer as fallback
    """
    with open(out_xml, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE fcpxml>\n')
        f.write('<fcpxml version="1.6">\n')
        f.write('  <resources>\n')
        
        # Add format
        f.write(f'    <format id="r1" name="FFVideoFormat1080p{int(fps)}" ')
        f.write(f'frameDuration="{int(1000/fps)}/1000s" width="1920" height="1080"/>\n')
        
        # Add assets
        for idx, item in enumerate(items):
            f.write(f'    <asset id="r{idx+2}" name="{item["file"]}" ')
            f.write(f'src="file://./{item["file"]}" hasVideo="1" format="r1"/>\n')
        
        f.write('  </resources>\n')
        f.write('  <library>\n')
        f.write('    <event name="Captions">\n')
        f.write('      <project name="Caption Timeline">\n')
        
        # Calculate duration
        if items:
            total_frames = max(item['end_frame'] for item in items)
            duration = total_frames / fps
        else:
            duration = 0
            
        f.write(f'        <sequence format="r1" duration="{duration:.3f}s">\n')
        f.write('          <spine>\n')
        
        # Add clips
        for idx, item in enumerate(items):
            start = item['start_frame'] / fps
            dur = (item['end_frame'] - item['start_frame']) / fps
            f.write(f'            <video name="{item["file"]}" offset="{start:.3f}s" ')
            f.write(f'ref="r{idx+2}" duration="{dur:.3f}s"/>\n')
        
        f.write('          </spine>\n')
        f.write('        </sequence>\n')
        f.write('      </project>\n')
        f.write('    </event>\n')
        f.write('  </library>\n')
        f.write('</fcpxml>\n')
    
    return out_xml
