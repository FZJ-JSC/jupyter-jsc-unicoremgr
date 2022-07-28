#!/bin/bash
echo "Hello World from my Script"

if [[ <hook_project_kernel> -eq 1 ]]; then
    echo "Use project kernel"
fi

if [[ <hook_multiple_keys> -eq 1 ]]; then
    echo "Use multiple_keys hook"
fi

#StageSpecific: <stage_stuff>
