# Pricing-state checks

See the parent README for exact reproduction commands, source pins and limits.
Requirements are pinned in requirements.txt. The fixture matrix includes
expected verdicts for both current upstream and the experimental schema.
All JSON Schema references resolve offline from the respective source trees.

The Python consumer map is an isolated reference, not a production cache or
buyer authentication system. Its ten tests exercise actual helper behavior;
they do not establish HTTP cache, transport or SDK conformance.
