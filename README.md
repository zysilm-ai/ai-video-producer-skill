# AI Video Producer

A Claude Code skill for complete AI video production workflows using Google Gemini and Veo APIs.

## Overview

This skill guides you through creating professional AI-generated videos with a structured, iterative workflow:

1. **Production Philosophy** - Define visual style, motion language, and narrative approach
2. **Scene Breakdown** - Decompose video into scenes with keyframe requirements
3. **Keyframe Generation** - Create start/end frames with visual consistency
4. **Video Synthesis** - Generate video segments using Veo API
5. **Review & Iterate** - Refine based on feedback

The philosophy-first approach ensures visual coherence across all scenes, resulting in professional, cohesive videos.

## Supported Video Types

- **Promotional** - Product launches, brand stories, ads
- **Educational** - Tutorials, explainers, courses
- **Narrative** - Short films, animations, music videos
- **Social Media** - Platform-optimized content (TikTok, Reels, Shorts)
- **Corporate** - Demos, presentations, training
- **Game Trailers** - Action sequences, atmosphere, gameplay hints

## Prerequisites

### 1. Google API Key

You need a Google API key with access to Gemini and Veo APIs.

1. Go to [Google AI Studio](https://aistudio.google.com/)
2. Create or select a project
3. Generate an API key
4. Enable Gemini and Veo APIs (Veo may require waitlist approval)

### 2. Python Environment

```bash
# Install dependencies
pip install -r requirements.txt

# Or install directly
pip install google-genai
```

### 3. Set Environment Variable

```bash
export GOOGLE_API_KEY="your-api-key-here"

# For persistence, add to your shell profile:
echo 'export GOOGLE_API_KEY="your-api-key"' >> ~/.bashrc
```

## Installation

### For Claude Code

Copy this skill to your Claude Code skills directory:

```bash
# Personal skills (available in all projects)
cp -r ai-video-producer ~/.claude/skills/

# Or project-specific skills
cp -r ai-video-producer /path/to/your/project/.claude/skills/
```

### For Other Environments

The scripts can be used standalone without Claude Code:

```bash
cd ai-video-producer

# Generate an image
python scripts/gemini_image.py --prompt "A sunset over mountains" --output sunset.png

# Generate a video
python scripts/veo_video.py --prompt "Camera slowly pans across mountain range at sunset" --output sunset.mp4
```

## Quick Start

### Step 1: Create Production Philosophy

Start by defining your visual style. Create a `style.json` file or use the example:

```bash
cp assets/example-style.json outputs/style.json
# Edit outputs/style.json with your project's visual direction
```

### Step 2: Plan Your Scenes

Break your video into scenes. For each scene, identify:
- Duration (max 8 seconds per segment)
- Required keyframes (start, end, or both)
- Motion/action description

### Step 3: Generate Keyframes

```bash
# Set your API key
export GOOGLE_API_KEY="your-key"

# Generate a starting keyframe
python scripts/gemini_image.py \
  --prompt "A warrior stands ready for battle, dramatic lighting" \
  --style-ref outputs/style.json \
  --output outputs/scene-01/keyframe-start.png
```

### Step 4: Generate Video

```bash
# Single-frame mode (start frame only)
python scripts/veo_video.py \
  --prompt "The warrior charges forward, cape flowing" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --style-ref outputs/style.json \
  --output outputs/scene-01/video.mp4

# Dual-frame mode (precise control)
python scripts/veo_video.py \
  --prompt "Warrior swings sword in powerful arc" \
  --start-frame outputs/scene-01/keyframe-start.png \
  --end-frame outputs/scene-01/keyframe-end.png \
  --output outputs/scene-01/video.mp4
```

### Step 5: Review and Iterate

Review the generated video. If adjustments are needed:
- Modify keyframes OR prompts (not both at once)
- Regenerate
- Repeat until satisfied

## Directory Structure

```
ai-video-producer/
├── SKILL.md                 # Core skill instructions for Claude
├── README.md                # This file
├── requirements.txt         # Python dependencies
├── LICENSE.txt              # MIT License
├── scripts/
│   ├── utils.py             # Shared utilities
│   ├── gemini_image.py      # Image generation
│   ├── veo_video.py         # Video generation
│   └── status_checker.py    # Check async job status
├── references/
│   ├── prompt-engineering.md    # Detailed prompt writing guide
│   ├── style-systems.md         # Visual consistency guide
│   └── troubleshooting.md       # Common issues and solutions
└── assets/
    └── example-style.json   # Example style configuration
```

## Script Reference

### gemini_image.py

Generate images for keyframes.

```bash
python scripts/gemini_image.py \
  --prompt "Description of the image" \
  --output path/to/output.png \
  [--style-ref path/to/style.json] \
  [--reference path/to/reference.png] \
  [--aspect-ratio 16:9|9:16|1:1|4:3]
```

### veo_video.py

Generate videos from prompts and/or keyframes.

```bash
python scripts/veo_video.py \
  --prompt "Description of motion and action" \
  --output path/to/output.mp4 \
  [--start-frame path/to/start.png] \
  [--end-frame path/to/end.png] \
  [--style-ref path/to/style.json] \
  [--duration 1-8] \
  [--resolution 720p|1080p] \
  [--no-audio]
```

### status_checker.py

Monitor async generation jobs.

```bash
# List recent operations
python scripts/status_checker.py list

# Check specific operation
python scripts/status_checker.py check <operation-name>
```

## Generation Strategies

| Scenario | Strategy | Keyframes |
|----------|----------|-----------|
| Continuous motion (running, flying) | Single-frame (start) | 1 |
| Ambient/atmospheric scenes | Single-frame (end) | 1 |
| Precise action/transformation | Dual-frame | 2 |
| Long take (>8 seconds) | Multi-segment | 3+ |

### Multi-Segment Long Takes

For sequences longer than 8 seconds, chain keyframes:

1. Define keyframes: A, B, C, D
2. Generate segments: A→B, B→C, C→D
3. Stitch in video editing software

## Workflow Tips

### Maintaining Consistency

1. **Create a style.json first** - Use it for all generations
2. **Generate all keyframes before videos** - Review for consistency
3. **Use reference images** - Provide character refs with `--reference`
4. **Copy style sections** - Keep style text identical across prompts

### Common Pitfalls

| Issue | Solution |
|-------|----------|
| Subject distorts on rotation | Add intermediate keyframe, limit rotation to <90° |
| Style drift between scenes | Reinforce style in every prompt |
| Unnatural motion | Add specific motion descriptors (speed, weight) |
| Audio mismatch | Add audio cues to prompt or use `--no-audio` |

### Prompt Writing

**Good prompt structure:**
```
[Subject]. [Action/motion]. [Environment]. [Style]. [Constraints].
```

**Example:**
```
A young woman in a flowing dress stands at cliff edge.
She slowly raises her arms as wind catches her hair.
Ocean waves crash below, dramatic clouds above.
Cinematic wide shot, golden hour, film grain.
Character remains facing ocean, no rotation.
```

See `references/prompt-engineering.md` for detailed guidance.

## API Costs

Approximate costs (as of late 2024):

| Service | Cost |
|---------|------|
| Gemini API (images) | Varies by model |
| Veo 2 (Gemini API) | ~$0.35/second of video |
| Veo 2 (Vertex AI) | ~$0.25-0.50/second |

Always confirm current pricing at [Google AI Pricing](https://ai.google.dev/pricing).

## Troubleshooting

### API Key Issues

```bash
# Verify key is set
echo $GOOGLE_API_KEY

# Test with a simple request
python -c "from google import genai; print(genai.Client(api_key='$GOOGLE_API_KEY'))"
```

### Generation Timeout

Increase max wait time:
```bash
python scripts/veo_video.py --prompt "..." --output out.mp4 --max-wait 900
```

### Rate Limiting

Wait 1-5 minutes and retry. Check quotas in Google Cloud Console.

See `references/troubleshooting.md` for more solutions.

## Using with Claude Code

When using this skill with Claude Code, simply describe what video you want to create. Claude will:

1. Help you develop a Production Philosophy
2. Guide you through scene planning
3. Generate keyframes and videos
4. Iterate based on your feedback

Example conversation:
```
You: I want to create a 30-second product demo for a smartwatch

Claude: I'll help you create a product demo video. Let's start by
establishing a Production Philosophy...
```

## Contributing

Contributions welcome! Areas for improvement:

- Additional video API integrations (Runway, etc.)
- Enhanced style transfer capabilities
- Audio generation integration
- Batch processing tools

## License

MIT License - See LICENSE.txt

## Acknowledgments

This skill was inspired by workflows shared by the AI video creation community, particularly the Gemini + Flow workflow for game trailer production.
