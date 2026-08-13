#!/usr/bin/env python
"""
Compatibility shim for `fit_marginal_advi` at bayesianquilts `7a29ec5`.

THE MISMATCH
------------
`IRTModel.fit_marginal_advi` is batchless. It closes over the full `data`
dict and builds

    def loss_fn(params): ...

then calls

    training_loop(initial_values=..., loss_fn=loss_fn,
                  num_epochs=..., learning_rate=...)

But `bayesianquilts.util.training_loop` at this commit is the *batched*
loop. It requires `data_iterator` and `steps_per_epoch` as positional
arguments, pulls `batch = next(data_iterator)` each step, and calls
`value_and_grad_fn(batch, params)` with `argnums=[1]`. So ADVI raises

    TypeError: training_loop() missing 2 required positional arguments:
               'data_iterator' and 'steps_per_epoch'

RELATION TO CHANG'S PATCH
-------------------------
`patch_all_training_loops_for_batchless_marginal_advi` in Chang's notebook
rewrites `loss_fn` to accept `(batch, params)` but never injects
`data_iterator` / `steps_per_epoch`, so on its own it does not fix this
error — it must have been written against a `training_loop` where those two
had defaults. This shim does both halves.

His second patch (`patch_tfp_transformed_distribution_entropy_for_advi`) is
NOT needed here: at `7a29ec5` `fit_marginal_advi` already sidesteps the
closed-form entropy with a Monte Carlo estimate,
`entropy = -jnp.mean(surrogate.log_prob(samples))`. Do not port it.

WHAT THE SHIM DOES
------------------
Wraps `bayesianquilts.util.training_loop` so that a call arriving without
`data_iterator` gets an endless iterator of an empty batch and
`steps_per_epoch=1`, and a one-argument `loss_fn` is widened to
`(batch, params)`. An empty dict is a valid JAX pytree, so `jax.jit` and
`value_and_grad(..., argnums=[1])` are unaffected — the batch is threaded
through and ignored, exactly as the batchless loss intends.

It is deliberately CONDITIONAL and LOUD. If a future bayesianquilts gives
`data_iterator` a default, `patch_batchless_training_loop()` detects that
and does nothing rather than silently layering a wrapper over working code.

KNOWN, NOT FIXED HERE
---------------------
`fit_marginal_advi` builds its PRNG key once outside `loss_fn`, so every
ADVI step reuses the same surrogate draws — the ELBO gradient is a
fixed-sample approximation rather than a fresh stochastic one. That is the
library's behaviour, not something this shim introduces. It is tolerable
because ADVI here is a 100-iteration warm-start and never the inference
(CLAUDE.md fact 7), but do not read the ADVI loss curve as a convergence
diagnostic.
"""
from __future__ import annotations

import inspect
import itertools

_PATCH_FLAG = "_mice_imp_batchless_advi"


def _needs_patch(fn) -> bool:
    """True iff training_loop still requires data_iterator with no default."""
    try:
        params = inspect.signature(fn).parameters
    except (TypeError, ValueError):
        return False
    p = params.get("data_iterator")
    return p is not None and p.default is inspect.Parameter.empty


def _is_batchless_loss(fn) -> bool:
    """True iff loss_fn takes exactly one positional parameter (params)."""
    try:
        params = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return False
    if any(p.kind is inspect.Parameter.VAR_POSITIONAL for p in params):
        return False
    positional = [
        p for p in params
        if p.kind in (inspect.Parameter.POSITIONAL_ONLY,
                      inspect.Parameter.POSITIONAL_OR_KEYWORD)
    ]
    return len(positional) == 1


def patch_batchless_training_loop(verbose: bool = True) -> bool:
    """Make `training_loop` accept the batchless call `fit_marginal_advi` makes.

    Idempotent. Returns True if the patch is now in force, False if the
    installed bayesianquilts does not need it.
    """
    from bayesianquilts import util

    original = util.training_loop

    if getattr(original, _PATCH_FLAG, False):
        return True

    if not _needs_patch(original):
        if verbose:
            print("compat: bayesianquilts.util.training_loop already accepts a "
                  "batchless call — no patch applied.")
        return False

    def training_loop(*args, **kwargs):
        # Only intervene on the batchless call shape. A caller that supplies
        # its own iterator is a genuinely batched fit and must pass through
        # untouched.
        if "data_iterator" not in kwargs and len(args) < 3:
            loss = kwargs.get("loss_fn")
            if loss is not None and _is_batchless_loss(loss):
                def batched_loss(batch, params):
                    return loss(params)
                kwargs["loss_fn"] = batched_loss

            kwargs.setdefault("data_iterator", itertools.repeat({}))
            kwargs.setdefault("steps_per_epoch", 1)

        return original(*args, **kwargs)

    setattr(training_loop, _PATCH_FLAG, True)
    training_loop._mice_imp_original = original
    util.training_loop = training_loop

    if verbose:
        print("compat: patched bayesianquilts.util.training_loop for the "
              "batchless marginal-ADVI call (see mice_imp/compat.py).")
    return True
