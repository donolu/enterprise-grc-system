# OpenAPI code generation

This directory contains the isolated, pinned toolchain used to generate the
frontend API declarations. It deliberately keeps `openapi-typescript` and its
TypeScript 5 peer dependency out of the application package.

From this directory, install the toolchain and generate the committed types:

```sh
npm ci
npm run generate
```

The frontend's `generate:api-types` script delegates here, and CI installs this
lockfile before checking that the generated declaration is current.
