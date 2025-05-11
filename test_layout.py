## layout
from shiny import App, ui

# Minimal working example for Shiny v1.1.0 to verify sidebar/main syntax
app_ui = ui.page_fluid(
    ui.layout_sidebar(
        sidebar=ui.sidebar(
            open="desktop",
            ui.input_slider("x", "Example slider", min=0, max=100, value=50),
        ),
        main=ui.main(
            ui.layout_columns(
                ui.card(
                    ui.card_header("Main Panel"),
                    "If you see this, the layout is valid!"
                ),
                col_widths=[12]
            )
        )
    )
)

app = App(app_ui, server=None)

