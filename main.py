import pyvista as pv
import numpy as np
import sys
import pyperclip
from pathlib import Path
from typing import *

class MeshVertexPicker:
    """Mesh vertex picker application for interactively selecting vertices from 3D mesh models."""
    
    def __init__(self, 
                 obj_file_path: Path,
                 window_size: tuple = (1024, 768)):
        """Initialize the MeshVertexPicker.
        
        Args:
            obj_file_path: Path to the OBJ file
            window_size: Window size as (width, height) tuple
        """

        self._mesh: Optional[pv.PolyData] = None
        self._plotter: Optional[pv.Plotter] = None
        self._text_actor = None
        self._selected_points: List[Dict] = []
        self._selected_point_actors: List = []
        self._multi_select_mode: bool = False

        # Load mesh
        try:
            obj_file_path = Path(obj_file_path).resolve()
            print(f'Loading OBJ file: {obj_file_path} ...')
            
            # Check if file exists
            if not obj_file_path.exists():
                raise FileNotFoundError(f'OBJ file not found: {obj_file_path}')
            
            try:
                self._mesh = pv.read(str(obj_file_path))
            except Exception as e:
                raise RuntimeError(f'Error occurred while loading OBJ file: {e}')

            # Validate mesh
            if self._mesh.n_points == 0:
                raise ValueError('Mesh has no valid points.')
        
        except Exception as e:
            raise Exception(f'Error loading mesh: {e}')

        # Setup plotter
        self._plotter = pv.Plotter(window_size=window_size, title=f'Mesh Vertex Picker - {obj_file_path.name}')
        self._plotter.add_title(obj_file_path.name, font_size=9, color='white')
        self._plotter.add_axes(interactive=True, color='white')
        self._plotter.set_background('black')
        self._plotter.enable_anti_aliasing('msaa')

        # Add mesh visualization to the plotter
        if self._mesh is None or self._plotter is None:
            raise RuntimeError("Mesh and plotter must be initialized first")
        
        # Add mesh with solid surface first
        self._plotter.add_mesh(self._mesh, style='surface', color='lightgray', opacity=1.0)

        # Add wireframe on top
        self._plotter.add_mesh(self._mesh, style='wireframe', color='white', line_width=1)
        
        # Add vertex points
        self._plotter.add_points(
            self._mesh.points,
            render_points_as_spheres=True,
            color='pink',
            point_size=5
        )

        # Enable point picking
        self._plotter.enable_point_picking(
            callback=self._on_pick_point, 
            show_message=False,
            show_point=False,
            left_clicking=False,
            use_picker=False,
            picker='point',
            tolerance=0.001
        )
        
        # Install keyboard event handlers
        self._plotter.add_key_event('m', lambda: self._on_toggle_multi_select())
        self._plotter.add_key_event('r', lambda: self._on_clear_selected_vertices())
        self._plotter.add_key_event('c', lambda: self._on_copy_selected_vertex_info())

        self._update_text_display()

        print(
            '\nInitialization complete. Usage instructions:\n'
            '1. When the window opens, press \'p\' key to switch to point selection mode.\n'
            '2. Click on any pink point to select it (will be highlighted in red).\n'
            '3. Press \'m\' key to toggle multi-select mode.\n'
            '4. Press \'r\' key to reset (clear) all selections.\n'
            '5. Press \'c\' key to copy selected vertex information to clipboard.'
        )

    def _select_vertex(self, vertex_id: int, picked_point: np.ndarray, vertex_pos: np.ndarray) -> None:
        """Select a vertex and add visual representation.
        
        Args:
            vertex_id: ID of the vertex to select
            picked_point: Original picked point coordinates
            vertex_pos: Actual vertex position coordinates
        """
        # Add new selection
        self._selected_points.append({
            'vertex_id': vertex_id,
            'picked_point': picked_point.copy(),
            'vertex_pos': vertex_pos.copy()
        })
        
        # Highlight selected vertex
        selected_point_actor = self._plotter.add_points(
            vertex_pos.reshape(1, 3),
            render_points_as_spheres=True,
            color='red',
            point_size=8
        )
        self._selected_point_actors.append(selected_point_actor)
    
    def _deselect_vertex(self, vertex_id: int) -> None:
        """Deselect a specific vertex.
        
        Args:
            vertex_id: ID of the vertex to deselect
        """
        # Remove vertex from selected points
        old_selected_points = self._selected_points.copy()
        new_selected_points = [sp for sp in old_selected_points if sp['vertex_id'] != vertex_id]

        # Remove corresponding actor if a vertex was actually removed
        if len(new_selected_points) <  len(old_selected_points):
            # Rebuild actors since we can't easily identify which actor corresponds to which vertex
            self._clear_selected_vertices()
            
            # Re-add actors for remaining selected points
            self._selected_points = new_selected_points
            for sp in self._selected_points:
                selected_point_actor = self._plotter.add_points(
                    sp['vertex_pos'].reshape(1, 3),
                    render_points_as_spheres=True,
                    color='red',
                    point_size=8
                )
                self._selected_point_actors.append(selected_point_actor)
   
    def _clear_selected_vertices(self) -> None:
        """Clear all selected points and their visual representations."""
        # Remove all previous selected point actors
        for actor in self._selected_point_actors:
            self._plotter.remove_actor(actor)
        self._selected_point_actors.clear()
        self._selected_points.clear()

    def _update_text_display(self) -> None:
        """Update the text display showing selected vertex information."""

        text_content = f'Multi-select mode: {"ON" if self._multi_select_mode else "OFF"}\n'
        if self._selected_points and len(self._selected_points) > 0:
            text_content += f'Selected {len(self._selected_points)} vertices:\n'
            
            # Max number of selections to display in text
            MAX_DISPLAY_COUNT = 20

            for i in range(min(len(self._selected_points), MAX_DISPLAY_COUNT)):
                sp = self._selected_points[i]
                text_content += f'  #{i+1} - ID: {sp["vertex_id"]}, Pos: ({sp["vertex_pos"][0]:.5f}, {sp["vertex_pos"][1]:.5f}, {sp["vertex_pos"][2]:.5f})\n'
            
            # If there are more than max display, skip the rest, only indicate how many more
            if len(self._selected_points) > MAX_DISPLAY_COUNT:
                remaining_count = len(self._selected_points) - MAX_DISPLAY_COUNT
                text_content += f'  (and {remaining_count} more...)\n'
        else:
            text_content += '(No vertices selected)\n'

        # Remove previous text (if exists)
        if self._text_actor is not None:
            self._plotter.remove_actor(self._text_actor)
        
        self._text_actor = self._plotter.add_text(
            text_content,
            position='upper_left',
            font_size=9,
            color='yellow',
            shadow=True
        )
    
    def _on_toggle_multi_select(self) -> None:
        """Toggle multi-select mode on/off."""
        self._multi_select_mode = not self._multi_select_mode
        status = "ON" if self._multi_select_mode else "OFF"
        print(f"Multi-select mode: {status}")
        self._update_text_display()

    def _on_clear_selected_vertices(self) -> None:
        """Clear all selected points and their visual representations."""
        self._clear_selected_vertices()
        self._update_text_display()

    def _on_copy_selected_vertex_info(self) -> None:
        """Copy selected vertex information to clipboard."""
        if not self._selected_points:
            print("No vertices selected to copy.")
            return
        
        # Format vertex information
        vertex_text = f'Selected {len(self._selected_points)} vertices\n'
        for i, sp in enumerate(self._selected_points):
            vertex_text += f'#{i+1} - ID: {sp["vertex_id"]}, Pos: ({sp["vertex_pos"][0]:.5f}, {sp["vertex_pos"][1]:.5f}, {sp["vertex_pos"][2]:.5f})\n'
        
        # Copy to clipboard
        try:
            pyperclip.copy(vertex_text)
            print(f"Copied {len(self._selected_points)} vertex info(s) to clipboard.")
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            print(vertex_text)

    def _on_pick_point(self, picked_point: np.ndarray) -> None:
        """Handle point picking event.
        
        Args:
            picked_point: The 3D coordinates of the picked point
        """
        try:
            # Find closest vertex to picked point
            vertex_id: int = self._mesh.find_closest_point(picked_point)
            if vertex_id == -1:
                print('No vertex found close to the picked point.')
                return

            vertex_pos: np.ndarray = self._mesh.points[vertex_id]

            # Check if this vertex is already selected
            already_selected: bool = any(sp['vertex_id'] == vertex_id for sp in self._selected_points)

            if already_selected:
                self._deselect_vertex(vertex_id)
            else:
                # If multi-select mode is not enabled, clear previous selections
                if not self._multi_select_mode:
                    self._clear_selected_vertices()
                
                self._select_vertex(vertex_id, picked_point, vertex_pos)
            
            # Update display text
            self._update_text_display()
                    
        except Exception as e:
            print(f'Error occurred during point selection: {e}')
 
    def show(self) -> bool:
        """Start the mesh vertex picker application.

        Returns:
            True if successful, False otherwise
        """
        try:
            self._plotter.show()
            return True
        except Exception as e:
            print(f'Exception: {e}')
            return False

def main(obj_file_path: Path) -> bool:
    picker = MeshVertexPicker(obj_file_path)
    return picker.show()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        obj_path = sys.argv[1]
    else:
        # mesh = pv.Cube()
        # obj_path = 'sample_obj/cube.obj'
        # mesh.save(obj_path)
        obj_path = 'sample_obj/bunny.obj'

    sys.exit(0 if main(obj_path) else -1)