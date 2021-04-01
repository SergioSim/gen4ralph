# Gen4Ralph

Gen4Ralph is a cli that generates edX JSON Schemas with `genson` and pydantic models with `datamodel-codegen` for [ralph](https://github.com/openfun/ralph).

# Example usage

cat tracking.log | ./bin/gen4ralph -v CRITICAL > edx.json
