from pathlib import Path
from typing import List, Dict, Tuple
from lxml import etree

def write_xmeml(items: List[Dict], fps_num: int, fps_den: int, out_xml: Path, out_dir: Path, dims: Tuple[int, int]):
    """Generate a Premiere Pro-compatible FCP 7 XML (XMEML) file."""
    xmeml = etree.Element("xmeml", version="5")
    sequence = etree.SubElement(xmeml, "sequence", id="CaptionTimeline")
    etree.SubElement(sequence, "name").text = "CaptionTimeline"
    
    is_ntsc = fps_den != 1
    timebase = round(fps_num / fps_den)

    rate = etree.SubElement(sequence, "rate")
    timebase_str = str(int(timebase))
    etree.SubElement(rate, "timebase").text = timebase_str
    etree.SubElement(rate, "ntsc").text = "TRUE" if is_ntsc else "FALSE"
    
    sequence_duration = items[-1]["end_frame"] if items else 0
    etree.SubElement(sequence, "duration").text = str(sequence_duration)

    timecode = etree.SubElement(sequence, "timecode")
    tc_rate = etree.SubElement(timecode, "rate")
    etree.SubElement(tc_rate, "timebase").text = timebase_str
    etree.SubElement(tc_rate, "ntsc").text = "TRUE" if is_ntsc else "FALSE"
    etree.SubElement(timecode, "string").text = "00:00:00:00"
    etree.SubElement(timecode, "frame").text = "0"
    etree.SubElement(timecode, "displayformat").text = "NDF"
    
    media = etree.SubElement(sequence, "media")
    video = etree.SubElement(media, "video")
    
    vid_format = etree.SubElement(video, "format")
    sample_chars = etree.SubElement(vid_format, "samplecharacteristics")
    etree.SubElement(sample_chars, "width").text = str(dims[0])
    etree.SubElement(sample_chars, "height").text = str(dims[1])
    etree.SubElement(sample_chars, "anamorphic").text = "FALSE"
    etree.SubElement(sample_chars, "pixelaspectratio").text = "square"
    etree.SubElement(sample_chars, "fielddominance").text = "none"
    
    track = etree.SubElement(video, "track")
    
    for idx, item in enumerate(items):
        start_frame = item["start_frame"]
        end_frame = item["end_frame"]
        duration = end_frame - start_frame
        
        clipitem = etree.SubElement(track, "clipitem", id=f"cap_{idx+1:04d}")
        etree.SubElement(clipitem, "name").text = item["file"]

        clip_rate = etree.SubElement(clipitem, "rate")
        etree.SubElement(clip_rate, "timebase").text = timebase_str
        etree.SubElement(clip_rate, "ntsc").text = "TRUE" if is_ntsc else "FALSE"

        etree.SubElement(clipitem, "duration").text = str(duration)
        etree.SubElement(clipitem, "start").text = str(start_frame)
        etree.SubElement(clipitem, "end").text = str(end_frame)
        etree.SubElement(clipitem, "in").text = "0"
        etree.SubElement(clipitem, "out").text = str(duration)

        sourcetrack = etree.SubElement(clipitem, "sourcetrack")
        etree.SubElement(sourcetrack, "mediatype").text = "video"
        etree.SubElement(sourcetrack, "trackindex").text = "1"
        
        etree.SubElement(clipitem, "alpha").text = "straight"
        
        file_el = etree.SubElement(clipitem, "file", id=f"file-{idx+1:04d}")
        etree.SubElement(file_el, "name").text = item["file"]
        
        abs_path = out_dir.resolve() / item["file"]
        etree.SubElement(file_el, "pathurl").text = abs_path.as_uri()
        
        file_rate = etree.SubElement(file_el, "rate")
        etree.SubElement(file_rate, "timebase").text = timebase_str
        etree.SubElement(file_rate, "ntsc").text = "TRUE" if is_ntsc else "FALSE"

        file_media = etree.SubElement(file_el, "media")
        file_video = etree.SubElement(file_media, "video")
        etree.SubElement(file_video, "duration").text = str(duration)
        file_sample_chars = etree.SubElement(file_video, "samplecharacteristics")
        etree.SubElement(file_sample_chars, "width").text = str(dims[0])
        etree.SubElement(file_sample_chars, "height").text = str(dims[1])
        etree.SubElement(file_sample_chars, "pixelaspectratio").text = "square"
        
    out_xml.write_bytes(etree.tostring(xmeml, pretty_print=True, xml_declaration=True, encoding="utf-8"))

