
# What is this?

It's a super light log forwarder for Splunk that uses HEC. It's got some
splunk-like features for field parsing and even has a bit of disk spooling.  It
will not integrate with the Splunk deployment mechanisms or anything useful like
that, and it will be missing tons of features (by comparison).

Personally, I've got these tiny T2.micros with a gig of ram. Splunk's light
forwarder can (in some situtations) take up a quarter of my ram, or half, ...
and I'm using such a tiny subset of the features in the Splunk forwarder and
have such a tiny message volume that it just seemed ridiculous.

YMMV.

You almost certainly want the real actual forwarder, not this, unless you're on
such a small VM that you fret over memory requirements. You want the real
forwarder if you're in production or have a boss that will make a frowny face
when you say things like "hand-rolled," "custom," "untested", or "open source."
