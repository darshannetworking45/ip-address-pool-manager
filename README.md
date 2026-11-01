# IPv4 Address Pool Manager

Maintains named IPv4 pools, allocates available addresses, tracks reservations and allocations, and persists state in JSON.

## Main entry points

- `src.pool.Allocation`
- `src.pool.AddressPool` (`allocate_next, release, stats`)
- `src.pool.PoolManager` (`add_pool, save, load`)

## Run the tests

```bash
python -m unittest discover -s tests -v
```

The project uses the Python standard library; no third-party package is required.

## Scope

The data store is a local JSON file. Use a shared IPAM source of truth when multiple automation workers need to allocate from the same pool.
