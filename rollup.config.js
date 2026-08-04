import deckyPlugin from "@decky/rollup";

const config = deckyPlugin({
  // Add your extra Rollup options here
});

// @decky/rollup defaults to Rollup's "smallest" treeshake preset.
// react-redux's ESM entry point wires up useSelector's real implementation
// via an import-time side effect (a bare `initializeUseSelector(...)` call);
// react-redux's package.json has no "sideEffects" field, so Rollup's
// aggressive preset appears to be pruning that call, leaving useSelector()
// pointed at react-redux's "notInitialized" stub, which throws
// "Error: uSES not initialized!" the first time useSelector() runs.
// A previous attempt to only override `moduleSideEffects` on top of the
// "smallest" preset did not fix this, so tree-shaking is disabled outright
// here instead of trying to find the exact minimal override. The bundle is
// small regardless (a single Decky plugin), so the size cost is negligible.
config.treeshake = false;

export default config;
