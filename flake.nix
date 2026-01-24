{
  description = "httpfilegen - CLI tool for generating HTTP files from OpenAPI specs";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
    home-manager = {
      url = "github:nix-community/home-manager";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs = { self, nixpkgs, flake-utils, home-manager }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        # Python 3.13 environment
        python = pkgs.python313;
        pyPkgs = python.pkgs;

        jsf = pyPkgs.buildPythonPackage rec {
          pname = "jsf";
          version = "0.11.2"; # adjust if needed

          src = pkgs.fetchPypi {
            inherit pname version;
            hash = "sha256-BwVbNjKB04zocaklagBYfYRygCxRCHIaf+WIRGUQS10=";
          };

          pyproject = true;
          build-system = with pyPkgs; [ setuptools wheel ];

          # Fix runtime deps check failure
          dependencies = with pyPkgs; [
            faker
            jsonschema
            pydantic
            pydantic-settings
            rstr
            smart-open
            typer
            typing-extensions
          ];

          doCheck = false;
        };

        # Development dependencies
        devDeps = with pkgs; [
          uv
          python
          git
          # Add any other dev tools
        ];

      in
      {
        # Home Manager module
        homeManagerModules.httpfilegen = { config, lib, ... }: {
          options.programs.httpfilegen = {
            enable = lib.mkEnableOption "httpfilegen CLI tool";

            package = lib.mkOption {
              type = lib.types.package;
              default = self.packages.${system}.default;
              description = "httpfilegen package to use";
            };

            # CLI option defaults
            defaults = {
              mode = lib.mkOption {
                type = lib.types.enum [ "default" "kulala" "pycharm" "vscode" ];
                default = "default";
                description = "Default editor mode: default (cross-compatible), kulala (Neovim), pycharm (JetBrains), vscode (httpyac)";
              };

              filemode = lib.mkOption {
                type = lib.types.enum [ "single" "multi" ];
                default = "single";
                description = "Default file generation mode";
              };

              baseUrl = lib.mkOption {
                type = lib.types.nullOr lib.types.str;
                default = null;
                description = "Default base URL for generated files";
              };

              envName = lib.mkOption {
                type = lib.types.str;
                default = "dev";
                description = "Default environment name";
              };

              includeExamples = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Default include-examples setting";
              };

              includeSchema = lib.mkOption {
                type = lib.types.bool;
                default = false;
                description = "Default include-schema setting";
              };
            };
          };

          config = lib.mkIf config.programs.httpfilegen.enable {
            home.packages = [ config.programs.httpfilegen.package ];

            xdg.configFile."httpfilegen/config.toml".source =
              (pkgs.formats.toml { }).generate "httpfilegen-config.toml"
                ({
                  mode = config.programs.httpfilegen.defaults.mode;
                  filemode = config.programs.httpfilegen.defaults.filemode;
                  env_name = config.programs.httpfilegen.defaults.envName;
                  include_examples = config.programs.httpfilegen.defaults.includeExamples;
                  include_schema = config.programs.httpfilegen.defaults.includeSchema;
                } // (lib.optionalAttrs (config.programs.httpfilegen.defaults.baseUrl != null) {
                  base_url = config.programs.httpfilegen.defaults.baseUrl;
                }));
          };
        };

        # Development shell
        devShells.default = pkgs.mkShell {
          packages = devDeps;

          shellHook = ''
            echo "🚀 httpfilegen development environment"
            echo "📦 Python: ${python.version}"
            echo "🛠️  uv available: $(uv --version)"
            echo ""
            echo "Commands:"
            echo "  uv sync --extra test    # Install dependencies"
            echo "  uv run pytest          # Run tests"
            echo "  uv run python -m cli   # Run CLI directly"
            echo ""
          '';
        };

        # Package build using setuptools
        packages.default = pyPkgs.buildPythonApplication {
          pname = "httpfilegen";
          version = "0.1.0";
          src = ./.;

          pyproject = true;
          build-system = with pyPkgs; [ setuptools wheel ];

          nativeBuildInputs = with pyPkgs; [
            pythonRelaxDepsHook
          ];

          pythonRelaxDeps = [
            "pydantic-settings"
            "typer"
          ];
          dependencies = with pyPkgs; [
            jsf
            openapi-pydantic
            openapi-spec-validator
            prance
            pydantic
            pydantic-settings
            typer
          ];

          nativeCheckInputs = with pyPkgs; [
            pytest
            pytest-cov
          ];

          makeWrapperArgs = [
            "--prefix PATH : ${python}/bin"
          ];

          meta = with pkgs.lib; {
            description = "CLI tool for generating HTTP files from OpenAPI specs";
            homepage = "https://github.com/your-repo/httpfilegen";
            license = licenses.mit;
            maintainers = [ ];
          };
        };
      });
}

