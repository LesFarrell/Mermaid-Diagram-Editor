```mermaid
flowchart TD
    Start[Start]
    Login[Open Login Screen]
    Check{Credentials valid?}
    Dashboard[Show Dashboard]
    Error[Show Error]
    Reports[Load Reports]
    End((End))
    Start --> Login
    Login --> Check
    Check -->|Yes| Dashboard
    Check -.->|No| Error
    Error --> Login
    Dashboard ==> Reports
    Reports --> End
```
