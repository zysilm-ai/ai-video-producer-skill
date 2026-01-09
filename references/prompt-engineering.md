# Prompt Engineering Guide for AI Video Production

This guide covers advanced prompt writing techniques for both image generation (Gemini) and video generation (Veo).

## Prompt Anatomy

A well-structured prompt contains these components in order:

```
[Subject] + [Action] + [Environment] + [Style] + [Technical] + [Constraints]
```

### Component Breakdown

#### 1. Subject Description
Be specific about the main subject. Include:
- Physical appearance
- Clothing/accessories
- Pose or stance
- Emotional state

**Weak**: "A person standing"
**Strong**: "A young woman with long dark hair wearing a flowing white dress, standing with arms slightly raised, serene expression"

#### 2. Action/Motion
For video prompts, describe the motion trajectory:
- Starting position
- Motion path
- Ending position (if not using end frame)
- Speed and quality of movement

**Weak**: "She moves"
**Strong**: "She slowly raises her arms from her sides to above her head, palms facing upward, movement fluid and graceful"

#### 3. Environment
Set the scene with:
- Location type
- Time of day
- Weather/atmosphere
- Foreground/background elements

**Weak**: "Outside"
**Strong**: "Standing at the edge of a cliff overlooking a stormy ocean, dark clouds gathering on the horizon, wind-swept grass in the foreground"

#### 4. Style Specification
Define the visual treatment:
- Art style (cinematic, animated, stylized)
- Color treatment (warm, cool, monochromatic)
- Mood (dramatic, peaceful, tense)
- Reference styles (optional)

**Weak**: "Nice looking"
**Strong**: "Cinematic wide shot, golden hour lighting, film grain, shallow depth of field, warm color grade with teal shadows"

#### 5. Technical Details
Camera and composition:
- Shot type (wide, medium, close-up)
- Camera movement (static, tracking, pan)
- Angle (eye-level, low angle, bird's eye)
- Aspect ratio considerations

**Weak**: (omitted)
**Strong**: "Medium wide shot, slight low angle, camera slowly dollies forward, 16:9 cinematic aspect ratio"

#### 6. Constraints
What to avoid or maintain:
- Elements to exclude
- Consistency requirements
- Directional locks

**Weak**: (omitted)
**Strong**: "Character remains facing the ocean throughout, no rotation. Avoid any modern elements. Maintain consistent lighting direction from upper left."

## Image Prompt Examples

### Character Portrait
```
A weathered sea captain in his 60s with a gray beard and deep-set eyes,
wearing a dark wool peacoat and captain's hat,
standing at the helm of a wooden sailing ship,
stormy seas visible through rain-spattered windows behind him.
Dramatic lighting from a lantern, chiaroscuro effect,
cinematic portrait shot, shallow depth of field.
Photorealistic, film grain, muted color palette with warm lamp light.
```

### Environment/Establishing Shot
```
An ancient temple partially reclaimed by jungle,
massive stone pillars wrapped in vines and moss,
shafts of golden sunlight piercing through the canopy above,
mist rising from the jungle floor.
Wide establishing shot, rule of thirds composition,
subject space on right for character entry.
Cinematic, Uncharted game aesthetic, lush greens with warm golden accents.
```

### Product Shot
```
A sleek smartwatch with a dark titanium case,
displayed on a marble surface with soft reflections,
minimalist background with subtle gradient from dark gray to black.
Product photography lighting with key light from upper right,
perfect focus on watch face showing 10:10 time.
Clean, modern, Apple product photography style.
```

## Video Prompt Examples

### Action Sequence (Dual-Frame)
```
The warrior springs forward from a crouching position,
sword drawn back for a powerful horizontal slash,
motion blur on the blade as it arcs through the air.
Enemies in the background begin to react, some raising shields.
Dust and debris kicked up from the warrior's movement.
Dynamic camera follows the action with slight shake.
Cinematic action, 300 movie style slow-motion aesthetic.
Warrior remains facing right throughout the sequence.
```

### Ambient/Atmospheric (Single-Frame)
```
Gentle waves lap against the shore as the sun sets,
colors shifting from orange to deep purple across the sky,
a lone sailboat silhouette drifts slowly across the horizon.
Seabirds occasionally pass through frame.
Camera remains static, contemplative mood.
Golden hour transitioning to blue hour,
film photography aesthetic, slight lens flare from sun.
```

### Product Demo (Text-to-Video)
```
A smartphone rotates slowly on a minimalist white surface,
light catching the metallic edges and creating subtle reflections,
camera orbits 180 degrees around the device.
Clean, modern lighting with soft shadows.
Apple-style product video aesthetic,
smooth continuous motion, no sudden changes.
```

### Character Transformation (Dual-Frame)
```
Starting: Young woman in casual modern clothes, confused expression.
Ending: Same woman now in elegant period dress, confident pose.

The transformation happens through a spiral of glowing particles
that swirl around her, briefly obscuring view before revealing the change.
Magical sparkle effects, warm golden light emanates from the transformation.
Fantasy movie aesthetic, Disney-quality visual effects.
Character position remains center frame throughout.
```

## Motion Description Vocabulary

### Speed Modifiers
- **Very slow**: "glacially", "imperceptibly", "in slow-motion"
- **Slow**: "gradually", "gently", "leisurely"
- **Normal**: "steadily", "smoothly", "naturally"
- **Fast**: "quickly", "swiftly", "rapidly"
- **Very fast**: "instantly", "in a flash", "explosively"

### Quality Modifiers
- **Smooth**: "fluid", "graceful", "seamless", "flowing"
- **Sharp**: "precise", "snappy", "crisp", "sudden"
- **Heavy**: "weighted", "powerful", "forceful", "impactful"
- **Light**: "delicate", "airy", "subtle", "ethereal"

### Directional Terms
- "moves from left to right across frame"
- "rises up from below frame"
- "retreats into the background"
- "approaches camera"
- "circles clockwise around"
- "descends diagonally toward lower right"

## Common Mistakes

### Mistake 1: Ambiguous Action
**Bad**: "The character does something dramatic"
**Good**: "The character throws both arms wide, head tilted back, mouth open in a triumphant shout"

### Mistake 2: Contradicting Keyframes
**Bad**: (Start frame shows character on left, prompt says they enter from right)
**Good**: Ensure prompt matches the visual information in keyframes

### Mistake 3: Impossible Physics
**Bad**: "Character instantly teleports across the room" (without magical context)
**Good**: "Character dashes across the room in a blur of speed, leaving a motion trail"

### Mistake 4: Too Many Actions
**Bad**: "Character jumps, spins, draws sword, blocks attack, and counterstrikes"
**Good**: Focus on one clear action per 8-second segment

### Mistake 5: Missing Constraints
**Bad**: "Character turns around"
**Good**: "Character rotates 90 degrees to face right, revealing profile view. Face should remain visible throughout rotation."

## Style Consistency Tips

1. **Create a prompt template** for your project with fixed style elements
2. **Copy-paste style sections** across all prompts in a project
3. **Reference previous outputs** as style guides when possible
4. **Use the style.json** configuration with the generation scripts
5. **Review each output** against the Production Philosophy before proceeding

## Negative Prompting

Veo and Gemini don't use traditional negative prompts. Instead, use explicit constraints:

**Instead of**: `negative_prompt: "blurry, low quality, distorted"`
**Use**: "Sharp focus, high quality, anatomically correct proportions. Avoid any blur or distortion."

**Instead of**: `negative_prompt: "text, watermark, logo"`
**Use**: "Clean image without any text, watermarks, or logos visible."

## Genre-Specific Prompt Strategies

Different genres require different prompt approaches. Use these guidelines when writing prompts for specific video types.

### Action Genre Prompts

**Emphasis**: Physical verbs, impact details, camera energy

**Key Vocabulary**:
- Motion verbs: lunges, slams, crashes, strikes, dodges, rolls, vaults, sprints, leaps
- Impact: shockwave ripples, debris scatters, dust explosion, impact frame, recoil
- Camera: "tracking intensifies", "camera shakes on impact", "handheld energy"

**Example Motion Prompt**:
```
Runner vaults over market stall in fluid motion, one hand pushing off wood for support.
Produce scatters from impact. Immediately weaves between crates.
Camera tracks the action with handheld energy, slight shake on landing.
Athletic, urgent movement. Urban chase aesthetic.
```

**Tips**:
- Describe physical body mechanics (arms pumping, legs driving)
- Include environmental interaction (debris, dust, objects displaced)
- Use active present-tense verbs

### Horror Genre Prompts

**Emphasis**: Atmosphere, restraint, negative space

**Key Vocabulary**:
- Atmosphere: shadow creeps, light flickers, darkness encroaches, mist rises
- Tension: barely visible, glimpse of, suggestion of, just at edge of frame
- Sound implications: silence broken by, faint sound of (visual cues for implied sound)

**Example Motion Prompt**:
```
Long hallway stretches into darkness. Single overhead light flickers twice.
Shadow moves almost imperceptibly at far end - was something there?
Camera remains static, slow zoom almost unnoticeable.
Tension builds through stillness. What lurks in darkness stays hidden.
```

**Tips**:
- Show less, imply more - restraint is power
- Use negative space (empty areas of frame create dread)
- Describe what ISN'T shown as much as what is
- Slow, deliberate motion builds tension

### Drama Genre Prompts

**Emphasis**: Subtle emotion, reactions, nuanced movement

**Key Vocabulary**:
- Subtle motion: eyes lower, hand trembles slightly, shoulders sag, breath catches
- Reactions: expression shifts from hope to resignation, realization dawns
- Stillness: moment of silence, weight of the moment, heavy pause

**Example Motion Prompt**:
```
Close-up on face as realization slowly dawns.
Eyes widen almost imperceptibly, then lower. Breath catches.
Slight tremor in lower lip. Swallow of emotion.
Camera holds steady, slow push-in barely noticeable.
Intimate moment of internal transformation.
```

**Tips**:
- Micro-expressions carry emotional weight
- Hold longer on reactions than actions
- Describe internal states through external cues
- Less movement often conveys more emotion

### Comedy Genre Prompts

**Emphasis**: Timing, exaggeration, full-body visibility

**Key Vocabulary**:
- Exaggeration: stumbles dramatically, flails wildly, double-takes, jaw drops
- Timing: beat, pause, sudden, perfectly timed
- Reactions: eyes go wide, frozen in place, slowly turns to look

**Example Motion Prompt**:
```
Character reaches for coffee cup without looking, hand finds empty air.
Pauses. Looks. Cup is gone. Eyes go wide in exaggerated surprise.
Head swivels searching. Spots cup on other side of table.
How did it get there? Confusion clear on face.
Camera holds wide to capture full body reaction.
```

**Tips**:
- Wide shots let audience see physical comedy
- Include "beat" moments - pauses for timing
- Exaggerate reactions (but not movement in I2V - the model does this naturally)
- Static camera lets the comedy speak

### Fantasy/Adventure Genre Prompts

**Emphasis**: Scale, majesty, heroic framing

**Key Vocabulary**:
- Scale: vast, towering, endless, majestic, epic
- Light: golden hour, rays of light, ethereal glow, magical shimmer
- Movement: sweeping, rising, soaring, billowing
- Hero: silhouette against sky, cloak flowing, determined stride

**Example Motion Prompt**:
```
Hero stands at cliff edge overlooking vast kingdom below.
Wind catches cloak, billowing dramatically behind.
Sun breaks through clouds, god rays streaming down.
Camera slowly rises, revealing epic scale of landscape.
Heroic low angle. Fantasy epic aesthetic.
```

**Tips**:
- Use environmental motion (wind, light, clouds) for dynamism
- Low angles create heroic framing
- Describe scale explicitly ("vast", "towering")
- Allow longer segments for establishing shots

### Anime Genre Prompts

**Emphasis**: Style signatures, dramatic poses, impact moments

**Key Vocabulary**:
- Style: speed lines, impact frame, dramatic pose, wind effect
- Motion: explosive movement, hair and clothes flowing, dramatic stillness
- Impact: shockwave, ground cracks, dust cloud, freeze moment

**Example Motion Prompt**:
```
Character in dramatic battle stance, sword raised.
Wind whips through hair and clothes dramatically.
Eyes narrow with determination. Subtle energy aura visible.
Hold on pose - this is THE moment before the strike.
Anime aesthetic, cel-shaded style, bold lines.
```

**Tips**:
- Anime uses dramatic static poses - describe the pose in detail
- Wind/cloth movement adds dynamism to still figures
- Reference anime-specific visual language (speed lines, impact frames)
- Exaggerated expressions are genre-appropriate

### Commercial/Product Genre Prompts

**Emphasis**: Clean presentation, aspirational context, premium feel

**Key Vocabulary**:
- Product: gleaming, pristine, crafted, precision, premium
- Detail: texture, material, finish, quality, craftsmanship
- Context: natural interaction, effortless, seamless integration
- Light: highlighting, accent light, soft shadow, clean

**Example Motion Prompt**:
```
Product rotates slowly on minimal white surface.
Professional lighting catches metallic edges.
Camera orbits smoothly, revealing form from all angles.
Clean, premium feel. Apple product video aesthetic.
Smooth continuous motion, unhurried, deliberate.
```

**Tips**:
- Slower, more deliberate motion for premium feel
- Clean backgrounds - nothing distracts from product
- Lifestyle shots should feel natural, not posed
- Light should highlight key features

## Adapting Prompts to Beat Types

Match your prompt's energy to the narrative beat:

| Beat Type | Prompt Energy | Example Approach |
|-----------|--------------|------------------|
| Setup | Establishing, calm | Slower motion, wider shots, scene-setting details |
| Action | Dynamic, focused | Active verbs, physical detail, camera energy |
| Reaction | Internal, held | Subtle motion, close framing, emotional cues |
| Transition | Bridging, smooth | Movement toward next location/moment |

**Setup Beat Example**:
```
Morning light filters through curtains into quiet bedroom.
Dust particles drift lazily in light beams.
Everything still, peaceful, undisturbed.
Camera holds wide, establishing the space.
```

**Action Beat Example**:
```
Door bursts open. Character rushes in, scanning room frantically.
Papers scatter from desk as hand sweeps across surface.
Urgent search, time running out. Camera tracks the chaos.
```

**Reaction Beat Example**:
```
Character freezes mid-search. Eyes lock on photograph.
Hand slowly reaches out, trembling slightly.
Face transforms as memory floods back.
Camera pushes in slowly on the realization.
```
