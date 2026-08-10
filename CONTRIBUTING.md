> [!IMPORTANT]
> **Note for contributors:** When branching out, create a new branch from the `dev` branch.

# 🎉 Welcome to **xinggraph**!

We're excited that you're interested in contributing to our project!
We want to ensure that every user and contributor feels welcome, included and supported to participate in xinggraph community.
This guide will help you get started and ensure your contributions can be efficiently integrated into the project.

## 🌟 Quick Links

- [Code of Conduct](CODE_OF_CONDUCT.md)
- [Discord Community](https://discord.gg/bcy8xFAtfd)
- [Issue Tracker](https://github.com/xing-kj/xinggraph/issues)
- [XingGraph Docs](https://docs.xinggraph.ai)

## 1. 🚀 Ways to Contribute

You can contribute to **xinggraph** in many ways:

- 📝 Submitting bug reports or feature requests
- 💡 Improving documentation
- 🔍 Reviewing pull requests
- 🛠️ Contributing code or tests
- 🌐 Helping other users

## 📫 Get in Touch

There are several ways to connect with the **xinggraph** team and community:

### GitHub Collaboration
- [Open an issue](https://github.com/xing-kj/xinggraph/issues) for bug reports, feature requests, or discussions
- Submit pull requests to contribute code or documentation
- Join ongoing discussions in existing issues and PRs

### Community Channels
- Join our [Discord community](https://discord.gg/bcy8xFAtfd) for real-time discussions
- Participate in community events and discussions
- Get help from other community members

### Direct Contact
- Email: contact@xinggraph.ai
- For business inquiries or sensitive matters, please reach out via email
- For general questions, prefer public channels like GitHub issues or Discord

We aim to respond to all communications within 2 business days. For faster responses, consider using our Discord channel where the whole community can help!

## Issue Labels

To help you find the most appropriate issues to work on, we use the following labels:

- `good first issue` - Perfect for newcomers to the project
- `bug` - Something isn't working as expected
- `documentation` - Improvements or additions to documentation
- `enhancement` - New features or improvements
- `help wanted` - Extra attention or assistance needed
- `question` - Further information is requested
- `wontfix` - This will not be worked on

Looking for a place to start? Try filtering for [good first issues](https://github.com/xing-kj/xinggraph/labels/good%20first%20issue)!


## 2. 🛠️ Development Setup

### Required tools
* [Python](https://www.python.org/downloads/)
* [uv](https://docs.astral.sh/uv/getting-started/installation/)
* pre-commit: `uv run pip install pre-commit && pre-commit install`

### Fork and Clone

1. Fork the [**xinggraph**](https://github.com/xing-kj/xinggraph) repository
2. Clone your fork:
```shell
git clone https://github.com/<your-github-username>/xinggraph.git
cd xinggraph
```
In case you are working on Vector and Graph Adapters
1. Fork the [**xinggraph-community**](https://github.com/xing-kj/xinggraph-community) repository
2. Clone your fork:
```shell
git clone https://github.com/<your-github-username>/xinggraph-community.git
cd xinggraph-community
```

### Create a Branch

Create a new branch for your work:
```shell
git checkout -b feature/your-feature-name
```

## 3. 🎯 Making Changes

1. **Code Style**: Follow the project's coding standards
2. **Documentation**: Update relevant documentation
3. **Tests**: Add tests for new features
4. **Commits**: Write clear commit messages

### Running Tests

Copy `.env.template` to `.env` and provide your OPENAI_API_KEY as LLM_API_KEY

```shell
uv run python xinggraph/tests/test_library.py
```

### Running Simple Example

Copy `.env.template` to `.env` and provide your OPENAI_API_KEY as LLM_API_KEY

Make sure to run ```shell uv sync ``` in the root cloned folder or set up a virtual environment to run xinggraph

```shell
uv run python examples/demos/simple_xinggraph_example.py
```

## 4. 📤 Submitting Changes

1. Make sure that `pre-commit` and hooks are installed. See `Required tools` section for more information. Try executing `pre-commit run` if you are not sure.
3. Push your changes:
```shell
git add .
git commit -s -m "Description of your changes"
git push origin feature/your-feature-name
```

2. Create a Pull Request:
   - Go to the [**xinggraph** repository](https://github.com/xing-kj/xinggraph) or [xinggraph community repository](https://github.com/xing-kj/xinggraph-community)
   - Click "Compare & Pull Request" and open a PR against dev branch
   - Fill in the PR template with details about your changes
   - You MUST provide screenshots of unit and integration tests passing on your machine. We can't merge PRs otherwise

> **Reviewers are auto-routed.** XingGraph uses a [`CODEOWNERS`](.github/CODEOWNERS)
> file to request reviews automatically based on the directories your PR touches.
> No manual ping required — the right person will get notified when you open the PR.

## 5. 📜 Developer Certificate of Origin (DCO)

All contributions must be signed-off to indicate agreement with our DCO:

```shell
git config alias.cos "commit -s"  # Create alias for signed commits
```

When your PR is ready, please include:
> "I affirm that all code in every commit of this pull request conforms to the terms of the XingGraph Developer Certificate of Origin"

## 6. 🤝 Community Guidelines

- Be respectful and inclusive
- Help others learn and grow
- Follow our [Code of Conduct](CODE_OF_CONDUCT.md)
- Provide constructive feedback
- Ask questions when unsure

## 7. 📫 Getting Help

- Open an [issue](https://github.com/xing-kj/xinggraph/issues)
- Join our Discord community
- Check existing documentation

Thank you for contributing to **xinggraph**! 🌟
