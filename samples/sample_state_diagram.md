```mermaid
stateDiagram-v2
    state Draft
    state Review
    state Approved
    state Published
    Draft --> Review : submit
    Review --> Draft : request changes
    Review --> Approved : approve
    Approved --> Published : release
```
