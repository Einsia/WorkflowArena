# Media evaluation runtime

The 32 content and 3D tasks use Gemini-3.8-Flash for their non-deterministic rubric items. Deterministic checks and group gates remain in each task. Acceptance requires the unrounded score to meet the paper threshold (document 75, video 90, 3D 80) and every critical item to pass. Incomplete grading produces no reward.

## Images

`images/manifest.json` records the original Linux/amd64 images by archive SHA256 and image ID. The two named archives accompany the local dataset in `../WorkflowArena-assets/`. Load them with:

```sh
python3 runtime/media/images/load_images.py --archive-dir ../WorkflowArena-assets
```

The loader validates both archives before loading either image, then verifies the resulting image IDs. The archives are separate from Git. `../WorkflowArena-assets/SHA256SUMS` also records their hashes.

The two Dockerfiles preserve the recovered build recipes. To rebuild:

```sh
docker build --platform linux/amd64 -t workflowarena-cdc-avb-repurpose:20261005 -f runtime/media/images/video-runtime.Dockerfile runtime/media/images
docker build --platform linux/amd64 -t workflowarena-original-cdc-tools:20261022 -f runtime/media/images/media-runtime.Dockerfile runtime/media/images
```

These recipes use floating upstream dependencies and do not recreate the locked historical image IDs. An original-image validation and a recipe rebuild are different checks.

## Judge configuration

Each task contains its judge client and acceptance code. Supply `GEMINI_API_KEY` to the separate verifier only, or mount a JSON configuration and set `WORKFLOWARENA_JUDGE_CONFIG` to its container path:

```json
{
  "base_url": "https://generativelanguage.googleapis.com",
  "key": "YOUR_VERIFIER_ONLY_KEY",
  "model": "gemini-3.8-flash",
  "expected_model_version": "gemini-3.8-flash-n"
}
```

The adapter uses the native generateContent protocol, validates completed JSON responses and the returned model version, and records model/usage metadata without credentials. Do not provide this configuration to the solver. A changed or unavailable model version is a grading error, not a failed task. The native protocol has been exercised with live text and image requests returning the locked model version. Actual rubric evaluations still require verifier credentials and access to that model service.
