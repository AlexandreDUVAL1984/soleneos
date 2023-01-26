from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout

# -----------------------------------------------------------------------------
# Get a server to work with
# -----------------------------------------------------------------------------

server = get_server()

from trame.app import get_server

from trame.ui.vuetify import SinglePageWithDrawerLayout
from trame.ui.router import RouterViewLayout
from trame.widgets import vtk, vuetify, trame, html, router

from vtkmodules.vtkRenderingCore import (
    vtkActor,
    vtkColorTransferFunction,
    vtkDataSetMapper,
    vtkRenderer,
    vtkRenderWindow,
    vtkRenderWindowInteractor,
)

from vtkmodules.vtkIOXML import vtkXMLUnstructuredGridReader
from vtkmodules.vtkCommonDataModel import vtkDataObject
from vtkmodules.vtkFiltersCore import vtkContourFilter
from vtkmodules.vtkCommonCore import vtkLookupTable
from vtkmodules.vtkCommonColor import vtkNamedColors
from vtkmodules.vtkRenderingAnnotation import vtkScalarBarActor
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleTrackballCamera


# Required for interactor initialization
from vtkmodules.vtkInteractionStyle import vtkInteractorStyleSwitch  # noqa

# Required for rendering initialization, not necessary for
# local rendering, but doesn't hurt to include it
import vtkmodules.vtkRenderingOpenGL2  # noqa

import pathlib

# -----------------------------------------------------------------------------
# Globals
# -----------------------------------------------------------------------------


class Representation:
    Points = 0
    Wireframe = 1
    Surface = 2
    SurfaceWithEdges = 3


class LookupTable:
    Rainbow = 0
    Inverted_Rainbow = 1
    Greyscale = 2
    Inverted_Greyscale = 3

class Data_Field: #For Confort DataSet
    Clodiffus =0
    CLoDirect = 1
    Humidite = 2
    Tair = 3
    Tse = 4
    Vitesse = 5
    Mrt = 6
    UTCI = 7

class UI:
    Title = "Visualisation"
    Bg_Color = "SlateGray"


# -----------------------------------------------------------------------------
# VTK pipeline
# -----------------------------------------------------------------------------

# Source/Reader
source_path = pathlib.Path(__file__).with_name("Tse_CLO_hparh_12h.vtu")
if not source_path.exists():
    raise FileNotFoundError(source_path.as_posix())


vtk_source = vtkXMLUnstructuredGridReader()
vtk_source.SetFileName(source_path.as_posix())
vtk_source.Update()
show_array = "CLO  (W/m2)"


# Misc stuff
colors = vtkNamedColors()

# Lookup table & color transfer function
num_colors = 256

ctf = vtkColorTransferFunction()
ctf.SetColorSpaceToDiverging()
ctf.AddRGBPoint(0.0, 0.230, 0.299, 0.754)
ctf.AddRGBPoint(1.0, 0.706, 0.016, 0.150)

lut = vtkLookupTable()
lut.SetNumberOfTableValues(num_colors)
lut.Build()

for i in range(0, num_colors):
    rgb = list(ctf.GetColor(float(i) / num_colors))
    rgb.append(1.0)
    lut.SetTableValue(i, *rgb)

# Extract Array/Field information

dataset_arrays = []
fields = [
    (vtk_source.GetOutput().GetPointData(), vtkDataObject.FIELD_ASSOCIATION_POINTS),
    (vtk_source.GetOutput().GetCellData(), vtkDataObject.FIELD_ASSOCIATION_CELLS),
]

for field in fields:
    field_arrays, association = field
    for i in range(field_arrays.GetNumberOfArrays()):
        array = field_arrays.GetArray(i)
        array_range = array.GetRange()
        dataset_arrays.append(
            {
                "text": array.GetName(),
                "value": i,
                "range": list(array_range),
                "type": association,
            }
        )
default_array = dataset_arrays[0]
default_min, default_max = default_array.get("range")
#scalar_range = vtk_source.GetOutput().GetScalarRange()


contour = vtkContourFilter()
contour.SetInputConnection(vtk_source.GetOutputPort())

mapper = vtkDataSetMapper()
mapper.SetInputConnection(vtk_source.GetOutputPort())
mapper.GetSelection
mapper.ScalarVisibilityOn()
mapper.SetScalarRange(default_min, default_max)
mapper.SetLookupTable(lut)


# Actors
actor = vtkActor()
actor.SetMapper(mapper)
# Mesh: Setup default representation to surface
actor.GetProperty().SetRepresentationToSurface()
actor.GetProperty().SetPointSize(1)
actor.GetProperty().EdgeVisibilityOn()



# Contour: Color by default array
mapper.SelectColorArray(default_array.get("text"))
mapper.GetLookupTable().SetRange(default_min, default_max)
if default_array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
    mapper.SetScalarModeToUsePointFieldData()
else:
    mapper.SetScalarModeToUseCellFieldData()
mapper.SetScalarVisibility(True)
mapper.SetUseLookupTableScalarRange(True)

scalar_bar = vtkScalarBarActor()
scalar_bar.SetLookupTable(mapper.GetLookupTable())
scalar_bar.SetNumberOfLabels(7)
scalar_bar.UnconstrainedFontSizeOn()
scalar_bar.SetMaximumWidthInPixels(100)
scalar_bar.SetMaximumHeightInPixels(800 // 3)
scalar_bar.SetTitle(default_array.get("text")) # TODO replace show_array


# max_scalar = scalar_range[1]
max_scalar = default_max+1
if max_scalar < 1:
    precision = 4
elif max_scalar < 10:
    precision = 3
elif max_scalar < 100:
    precision = 2
else:
    precision = 1
scalar_bar.SetLabelFormat(f"%-#6.{precision}f")

# Render stuff
renderer = vtkRenderer()
renderer.SetBackground(colors.GetColor3d(UI.Bg_Color)) 
renderer.AddActor(actor)
renderer.AddActor2D(scalar_bar)

render_window = vtkRenderWindow()
render_window.SetSize(300, 300)
render_window.AddRenderer(renderer)
render_window.SetWindowName("VTK Test")

render_window_interactor = vtkRenderWindowInteractor()
interactor_style = vtkInteractorStyleTrackballCamera()
render_window_interactor.SetInteractorStyle(interactor_style)
render_window_interactor.SetRenderWindow(render_window)
renderer.ResetCamera()

# -----------------------------------------------------------------------------
# Trame setup
# -----------------------------------------------------------------------------

server = get_server()
state, ctrl = server.state, server.controller

state.setdefault("active_ui", UI.Title)
state.vtk_bground = UI.Bg_Color

# -----------------------------------------------------------------------------
# Callbacks
# -----------------------------------------------------------------------------

# Representation Callbacks
def update_representation(actor, mode):
    property = actor.GetProperty()
    if mode == Representation.Points:
        property.SetRepresentationToPoints()
        property.SetPointSize(5)
        property.EdgeVisibilityOff()
    elif mode == Representation.Wireframe:
        property.SetRepresentationToWireframe()
        property.SetPointSize(1)
        property.EdgeVisibilityOff()
    elif mode == Representation.Surface:
        property.SetRepresentationToSurface()
        property.SetPointSize(1)
        property.EdgeVisibilityOff()
    elif mode == Representation.SurfaceWithEdges:
        property.SetRepresentationToSurface()
        property.SetPointSize(1)
        property.EdgeVisibilityOn()


@state.change("mesh_representation")
def update_mesh_representation(mesh_representation, **kwargs):
    update_representation(actor, mesh_representation)
    ctrl.view_update()

# Mesh_data Callbacks
@state.change("Mesh_data_by_array_idx")
def update_contour_by(Mesh_data_by_array_idx, **kwargs):
    array = dataset_arrays[Mesh_data_by_array_idx]
    contour_min, contour_max = array.get("range")
    #contour_step = 0.01 * (contour_max - contour_min)
    contour_value = 0.5 * (contour_max + contour_min)
    mapper.SetInputArrayToProcess(0, 0, 0, array.get("type"), array.get("text"))
    contour.SetValue(0, contour_value)
    ctrl.view_update()


# Color By Callbacks
def color_by_array(actor, array):
    _min, _max = array.get("range")
    mapper = actor.GetMapper()
    mapper.SelectColorArray(array.get("text"))
    mapper.GetLookupTable().SetRange(_min, _max)
    if array.get("type") == vtkDataObject.FIELD_ASSOCIATION_POINTS:
        mapper.SetScalarModeToUsePointFieldData()
    else:
        mapper.SetScalarModeToUseCellFieldData()
    mapper.SetScalarVisibility(True)
    mapper.SetUseLookupTableScalarRange(True)


# Opacity Callbacks
@state.change("mesh_opacity")
def update_mesh_opacity(mesh_opacity, **kwargs):
    actor.GetProperty().SetOpacity(mesh_opacity)
    ctrl.view_update()


def toggle_background():
    bgcolor = "SlateGray"
    if state.vtk_bground == "SlateGray":
        bgcolor = "black"

    state.vtk_bground = bgcolor
    renderer.SetBackground(colors.GetColor3d(bgcolor))

    ctrl.view_update()


# -----------------------------------------------------------------------------
# GUI ELEMENTS
# -----------------------------------------------------------------------------


def ui_card(title, ui_name):
    with vuetify.VCard(to="/", v_show=f"active_ui == '{ui_name}'"):
        vuetify.VCardTitle(
            title,
            classes="grey lighten-1 py-1 grey--text text--darken-3",
            style="user-select: none; cursor: pointer",
            hide_details=True,
            dense=True,
        )
        content = vuetify.VCardText(classes="py-2")
    return content


def mesh_card():
    with ui_card(title=UI.Title, ui_name=UI.Title):

        with vuetify.VRow(classes="pt-2", dense=True):
            vuetify.VSelect(
                # Representation
                v_model=("mesh_representation", Representation.Surface),
                items=(
                    "representations",
                    [
                        {"text": "Points", "value": 0},
                        {"text": "Wireframe", "value": 1},
                        {"text": "Surface", "value": 2},
                        {"text": "Surface With Edges", "value": 3},
                    ],
                ),
                label="Representation",
                hide_details=True,
                dense=True,
                outlined=True,
                classes="pt-1",
            )

        vuetify.VSlider(
            # Opacity
            v_model=("mesh_opacity", 1.0),
            min=0,
            max=1,
            step=0.1,
            label="Opacity",
            classes="mt-1",
            hide_details=True,
            dense=True,
        )
        vuetify.VSelect(
                    # Contour By
                    label="Variables",
                    v_model=("Mesh_data_by_array_idx", 0),
                    items=("array_list", dataset_arrays),
                    hide_details=True,
                    dense=True,
                    outlined=True,
                    classes="pt-1",
                )

# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

with RouterViewLayout(server, "/"):
    with html.Div(style="height: 100%; width: 100%;"):
        view = vtk.VtkLocalView(render_window)
        ctrl.view_update.add(view.update)
        ctrl.on_server_ready.add(view.update)

with RouterViewLayout(server, "/foo"):
    with vuetify.VCard():
        vuetify.VCardTitle("This is foo")
        with vuetify.VCardText():
            vuetify.VBtn("Take me back", click="$router.back()")


with SinglePageWithDrawerLayout(server) as layout:
    layout.title.set_text("SOLENEOS PoC")

    with layout.toolbar as toolbar:
        toolbar.dense = True
        vuetify.VSpacer()
        vuetify.VDivider(vertical=True, classes="mx-2")
        vuetify.VSwitch(
            v_model=("$vuetify.theme.dark"),
            inset=True,
            hide_details=True,
            dense=True,
            change=toggle_background,
        )

    with layout.drawer as drawer:
        drawer.width = 325
        with vuetify.VList(shaped=True, v_model=("selectedRoute", 0)):
            with vuetify.VListGroup(value=("true",), sub_group=True):
                with vuetify.Template(v_slot_activator=True):
                    vuetify.VListItemTitle("Vue 3D")
                mesh_card()

    with layout.content:
        with vuetify.VContainer(fluid=True, classes="pa-0 fill-height"):
            router.RouterView(style="width: 100%; height: 100%")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
# -----------------------------------------------------------------------------
# GUI
# -----------------------------------------------------------------------------

with SinglePageLayout(server) as layout:
    layout.title.set_text("Hello trame")

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    server.start()
