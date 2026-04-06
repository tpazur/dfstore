# TODO

## Planned Features

### Multiple Stages
Support named stages (e.g. `prod`, `dev`) and any user-defined mirror, so a single codebase can read/write to different stores by stage without changing call sites.

```python
dfstore.save(df, name="sales", stage="prod")
dfstore.get("sales", stage="dev")
```

### Remote Server
Allow dfstore to read and write DataFrames from a central remote host, enabling shared access across machines and team members — while keeping the zero-infrastructure feel for local use.

```python
dfstore.save(df, name="sales", store_path="https://myhost:7860")
dfstore.get("sales", store_path="https://myhost:7860")
```
