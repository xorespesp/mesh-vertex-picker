import pyvista as pv
import numpy as np
import sys
from pathlib import Path
from typing import *

def main(obj_file_path: Path) -> bool:
    try:
        obj_file_path = Path(obj_file_path).resolve()
        
        print(f'Loading OBJ file: {obj_file_path} ...')
        
        # Check if file exists
        if not obj_file_path.exists():
            raise FileNotFoundError(f'OBJ file not found: {obj_file_path}')
        
        try:
            mesh: pv.PolyData = pv.read(str(obj_file_path))
        except Exception as e:
            raise RuntimeError(f'Error occurred while loading OBJ file: {e}')

        # Validate mesh
        if mesh.n_points == 0:
            raise ValueError('Mesh has no valid points.')

        plotter: pv.Plotter = pv.Plotter(window_size=[1024, 768], title='Mesh Vertex Picker')
        plotter.add_title(f'{obj_file_path.name}', font_size=9, color='white')
        plotter.add_axes(interactive=True, color='white')
        plotter.set_background('black')
        plotter.enable_anti_aliasing('msaa')
        
        # Text actor reference for updating
        text_actor = None
        selected_point_actor = None  # Actor to display selected points

        def on_pick(picked_point: np.ndarray) -> None:
            nonlocal text_actor, selected_point_actor

            try:
                # NOTE: `picked_point` is the [x, y, z] coordinate array itself.
                vertex_id: int = mesh.find_closest_point(picked_point)
                if vertex_id == -1:
                    print('No vertex found close to the picked point.')
                    return

                vertex_pos: np.ndarray = mesh.points[vertex_id]

                # Remove previous selected point if exists
                if selected_point_actor is not None:
                    plotter.remove_actor(selected_point_actor)

                # Remove previous text if exists
                if text_actor is not None:
                    plotter.remove_actor(text_actor)
                
                # Remove previous selected point if exists
                if selected_point_actor is not None:
                    plotter.remove_actor(selected_point_actor)
                
                # Add text to plotter showing selected vertex info
                text_content = (
                    f'Picked Point: ({picked_point[0]:.4f}, {picked_point[1]:.4f}, {picked_point[2]:.4f})\n'
                    f'Vertex ID: {vertex_id} / {len(mesh.points) - 1}\n'
                    f'Vertex Pos: ({vertex_pos[0]:.4f}, {vertex_pos[1]:.4f}, {vertex_pos[2]:.4f})'
                )
                text_actor = plotter.add_text(
                    text_content,
                    position='upper_left',
                    font_size=9,
                    color='yellow',
                    shadow=True
                )
                
                # Highlight selected vertex in blue
                selected_point_actor = plotter.add_points(
                    vertex_pos.reshape(1, 3),
                    render_points_as_spheres=True,
                    color='red',
                    point_size=7
                )
            except Exception as e:
                print(f'Error occurred during point selection: {e}')

        # Add mesh with solid surface first
        plotter.add_mesh(mesh, style='surface', color='lightgray', opacity=1.0)

        # Add wireframe on top
        plotter.add_mesh(mesh, style='wireframe', color='white', line_width=1)
        
        plotter.add_points(
            mesh.points,
            render_points_as_spheres=True,
            color='pink',
            point_size=5
        )

        # Ref: https://docs.pyvista.org/api/plotting/_autosummary/pyvista.plotter.enable_point_picking#pyvista.Plotter.enable_point_picking
        plotter.enable_point_picking(
            callback=on_pick, 
            show_message=False,
            show_point=False,
            left_clicking=False,
            use_picker=False,
            picker='point',
            tolerance=0.001
        )

        print(
            '\nInitialization complete. Usage instructions:\n'
            '1. When the window opens, press \'p\' key to switch to point selection mode.\n'
            '2. Click on any red point to see its ID printed in the terminal.\n'
        )
        
        plotter.show()
        return True
    except Exception as e:
        print(f'Exception: {e}')
        return False


if __name__ == '__main__':
    if len(sys.argv) > 1:
        obj_path = sys.argv[1]
    else:
        # mesh = pv.Cube()
        # obj_path = 'sample_obj/cube.obj'
        # mesh.save(obj_path)
        obj_path = 'sample_obj/bunny.obj'

    sys.exit(0 if main(obj_path) else -1)