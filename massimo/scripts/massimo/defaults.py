"""
MIT License

Copyright (c) 2022 Michael Malinowski

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# ----------------------------------------------------------------------------------------------------------------------
class Defaults(object):
    """
    This class stores a series of likely default weight/mass values for
    sections of bodies. Its not bullet proof, but if fairly standard naming
    conventions are used then we'll try and give the user a reasonable weight
    based on a biped
    """
    _VALUES = dict(
        belly=8.6,
        torso=8.6,
        hip=8.6,
        lower_body=8.6,
        chest=10,
        upper_body=10,
        body=18.6,
        upper_arm=0.6,
        arm_upper=0.6,
        humerus=0.6,
        lower_arm=0.4,
        arm_lower=0.4,
        forearm=0.4,
        hand=0.2,
        upper_leg=1.9,
        leg_upper=1.9,
        femur=1.9,
        thigh=1.9,
        lower_leg=1.0,
        leg_lower=1.0,
        calf=1.0,
        foot=0.5,
        feet=0.5,
        head=3.9,
    )

    # ------------------------------------------------------------------------------------------------------------------
    @classmethod
    def get(cls, value):
        for item in cls._VALUES:

            # -- Each item can be represented in multiple ways, such as with spaces, no spaces
            # -- underscores etc, so lets try and resolve that
            matchable_alternatives = [
                item,
                item.replace('_', ''),
                item.replace('_', ' '),
            ]
            for matchable_item in matchable_alternatives:
                if matchable_item in value.lower():
                    return cls._VALUES[item]

        # -- In the instance where no match was found, we simply
        # -- give a value of 1.0 as a default
        return 1.0
