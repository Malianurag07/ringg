# Voice-over script for the "Computer Vision for Ring Side Identification and Angular Orientation" video.
# One entry per scene: (on-screen title, [spoken sentences]).
# Spoken text uses US spellings so the TTS pronounces them correctly.
SCRIPT = [
    ('Computer Vision for Ring Side Identification and Angular Orientation', [
        'Hi there.',
        'This is Computer Vision for Ring Side Identification and Angular Orientation, by V7 AI Solutions, with Technocraft.',
        'Please note, this is a theoretical estimate, visualized to help define the scope.',
        'First the setup, then the journey of a ring.',
    ]),
    ('A · Setup: the hardware', [
        'First, the hardware.',
        'Two cameras sit above the belt, in vibration-isolated frames, with light-tight shrouds.',
        'Camera one has a low-angle ring light. Camera two has a diffuse light.',
        'A presence sensor sits just before camera one, and a belt encoder is added, if the line has none.',
        'Everything connects through an Ethernet switch to the server, in a cooled cabinet with a UPS.',
        "The ML models are trained beforehand, on a development server with a GPU card, using images of Technocraft's sample rings.",
        'V7 AI Solutions specifies the hardware, and Technocraft procures it.',
    ]),
    ('A · Setup: teaching the system', [
        'Next, a one-time software setup.',
        'A ring of known size sets the scale, from pixels to millimeters.',
        'Each of the five ring types is recorded: its outline, its notches, and its target angle.',
        'The trigger delay is set, and the rotation direction is agreed with the Technocraft team.',
        'Finally, the signal link with the line controller is agreed, including what happens if it drops.',
    ]),
    ('B · A ring arrives', [
        "Now, let's follow one ring. A new ring arrives about every six seconds.",
        'It lands at a random spot, either side up.',
        "When it breaks the sensor beam, a pulse goes to camera one's trigger.",
        'The software logs it, gives it an ID, and counts it.',
        'Then, using encoder pulses, it waits until the ring is centered under camera one.',
    ]),
    ('B · Camera 1 takes the picture', [
        'Camera one fires.',
        'A strobe flash of about point two milliseconds freezes the ring, on the moving belt.',
        'The low-angle light makes the burr edge stand out clearly.',
        'The twelve-megapixel image reaches the server in about a tenth of a second.',
    ]),
    ('B · The server checks the image', [
        'Now, the server checks the image.',
        'Is there exactly one complete ring in view?',
        'Where is it, and which of the five types is it?',
        'And which side is up, burr or rollover, with a confidence score.',
        'All of this, in under a second.',
    ]),
    ('B · Signal 1 and the flip', [
        'If the side check is clear, signal one goes to the line controller. Flip, yes or no.',
        'If not, for example, a low confidence score, no ring, or two rings, the system raises an alert, and a diverter flap pushes the ring into a separate section.',
        'The flipper then turns burr-up rings over. Rollover-up rings pass straight through.',
    ]),
    ('B · Camera 2 takes the picture', [
        'Camera two is triggered by the flipper trigger. From that moment, the software calculates the delay in encoder pulses, and captures the image when the ring is centered.',
        'Camera two is also twelve megapixels, with a diffuse strobe, for a clean outline of the notches.',
        'And again, the image goes through the switch, to the server.',
    ]),
    ('B · Measuring the angle', [
        'Now, the angle.',
        'The software finds the notches, and works out how far the ring must turn, from zero to about eighty-nine degrees, always in the agreed direction.',
        "The notches are found by an ML model, trained on images of Technocraft's sample rings.",
        "The result is matched to the ring's ID, so the right angle goes with the right ring.",
    ]),
    ('B · Signal 2 and the robot', [
        'Signal two sends the rotation angle to the robot.',
        'The robot picks up the ring, turns it by that angle, and places it onto the pins.',
        'One ring done. About six seconds later, the next one arrives.',
    ]),
    ('C · Running in the background', [
        'Some things run in the background, all the time.',
        'Every image, decision, confidence score and signal is logged, by ring ID.',
        'The sensor count is compared with the rings processed, so no ring is missed unnoticed.',
        'The confidence score is tracked over time, and an alarm is raised as soon as it suddenly dips, for example, from rust or a failing light.',
        'A heartbeat between the server and the line controller triggers a safe stop, if the link drops.',
        'The operator screen shows live status, alerts, and recovery steps.',
        'If the power goes out, the UPS keeps the server running, uninterrupted.',
    ]),
    ('B · The full flow', [
        'Now, the full flow.',
        'Each ring is detected, gets its ID, and camera one checks which side is up.',
        'Burr-up rings are flipped. Rollover-up rings pass straight through.',
        'Camera two measures the angle, and the robot places each ring in its own slot.',
        'All rings, rollover side up, at the right angle, each in its own slot.',
    ]),
    ('D · Why the GPU is needed', [
        'So, why do we need a GPU?',
        'Rings can have rust, oil, scratches, and changing light. A trained ML model copes with this far better than fixed rules.',
        "The models are trained beforehand, on a development server with a GPU card, using images of Technocraft's sample rings.",
        'Training means millions of calculations over thousands of images. A GPU does them in parallel, so it is much faster.',
        "On the line, the server's GPU runs the models quickly and consistently, while the CPU handles the cameras, signals and logging.",
        'For a new ring type, Technocraft provides sample rings, and the model is retrained on the development server.',
        'So, the GPU makes accurate, reliable ML possible, without slowing the line.',
    ]),
    ('Who owns which part of the solution', [
        'So, who owns which part of the solution?',
        'V7 AI Solutions owns all the vision software, from the sensor event to the two signals.',
        'Technocraft owns the conveyor, flipper, robot, line controller and pins, and procures the hardware.',
        'Thank you for watching.',
    ]),
]
