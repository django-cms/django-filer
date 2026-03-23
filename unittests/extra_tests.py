# def test_erase_trash_folder_with_folders(admin_client, admin_user, uploaded_file, sub_folder):
#     """Test erasing a trash folder containing folders."""
#     ambit = sub_folder.get_ambit()
#
#     # Create folders to be deleted
#     created_folders = []
#     for i in range(1, 3):
#         folder = FolderModel.objects.create(
#             parent=sub_folder,
#             name=f"folder_to_erase_{i}",
#             owner=admin_user,
#             ordering=i,
#         )
#         # Add a file to each folder
#         FileModel.objects.create(
#             parent=folder,
#             name=f"file_in_folder_{i}.txt",
#             file_size=uploaded_file.file_size,
#             sha1=uploaded_file.sha1,
#             owner=admin_user,
#         )
#         created_folders.append(folder)
#
#     # Delete the folders to move them to trash
#     admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
#     response = admin_client.post(
#         f'{admin_url}/delete',
#         json.dumps({'inode_ids': [str(f.id) for f in created_folders]}),
#         content_type='application/json',
#     )
#     assert response.status_code == 200
#
#     # Verify folders are in trash
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#     trash_folders = list(trash_folder.listdir(name__startswith='folder_to_erase', is_folder=True))
#     assert len(trash_folders) == len(created_folders)
#
#     # Verify DiscardedInode records exist for folders
#     assert DiscardedInode.objects.filter(inode__in=[f.id for f in created_folders]).count() == len(created_folders)
#
#     # Erase the trash folder
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#     erase_response = admin_client.delete(f'{trash_url}/erase_trash_folder')
#     assert erase_response.status_code == 200
#
#     # Verify folders are deleted from trash
#     remaining_folders = list(trash_folder.listdir(name__startswith='folder_to_erase', is_folder=True))
#     assert len(remaining_folders) == 0
#
#     # Verify DiscardedInode records are deleted
#     assert DiscardedInode.objects.filter(inode__in=[f.id for f in created_folders]).count() == 0
#
#     # Verify folders are no longer in database
#     assert FolderModel.objects.filter(id__in=[f.id for f in created_folders]).count() == 0
#
#
# def test_erase_trash_folder_with_mixed_content(admin_client, admin_user, uploaded_file, sub_folder):
#     """Test erasing a trash folder containing both files and folders."""
#     ambit = sub_folder.get_ambit()
#
#     # Create files
#     created_files = FileModel.objects.bulk_create([
#         FileModel(
#             parent=sub_folder,
#             name=f"mixed_file_{i}.txt",
#             file_size=uploaded_file.file_size,
#             sha1=uploaded_file.sha1,
#             owner=admin_user,
#         ) for i in range(1, 3)
#     ])
#
#     # Create folders with files inside
#     created_folders = []
#     for i in range(1, 3):
#         folder = FolderModel.objects.create(
#             parent=sub_folder,
#             name=f"mixed_folder_{i}",
#             owner=admin_user,
#         )
#         FileModel.objects.create(
#             parent=folder,
#             name=f"inner_file_{i}.txt",
#             file_size=uploaded_file.file_size,
#             sha1=uploaded_file.sha1,
#             owner=admin_user,
#         )
#         created_folders.append(folder)
#
#     all_inodes = created_files + created_folders
#
#     # Delete all inodes
#     admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
#     response = admin_client.post(
#         f'{admin_url}/delete',
#         json.dumps({'inode_ids': [str(i.id) for i in all_inodes]}),
#         content_type='application/json',
#     )
#     assert response.status_code == 200
#
#     # Verify content is in trash
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#     trash_content = list(trash_folder.listdir())
#     assert len(trash_content) == len(all_inodes)
#
#     # Erase the trash folder
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#     erase_response = admin_client.delete(f'{trash_url}/erase_trash_folder')
#     assert erase_response.status_code == 200
#
#     # Verify all content is deleted
#     remaining_content = list(trash_folder.listdir())
#     assert len(remaining_content) == 0
#
#     # Verify all DiscardedInode records are deleted
#     assert DiscardedInode.objects.filter(inode__in=[i.id for i in all_inodes]).count() == 0
#
#     # Verify files and folders are no longer in database
#     assert FileModel.objects.filter(id__in=[i.id for i in created_files]).count() == 0
#     assert FolderModel.objects.filter(id__in=[i.id for i in created_folders]).count() == 0
#
#
# def test_erase_trash_folder_with_wrong_method(admin_client, admin_user):
#     """Test that erase_trash_folder rejects non-DELETE methods."""
#     ambit_qs = admin_user.ambits.all()
#     if not ambit_qs.exists():
#         pytest.skip("Admin user has no ambits")
#     ambit = ambit_qs.first()
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#
#     # Test POST method
#     post_response = admin_client.post(f'{trash_url}/erase_trash_folder')
#     assert post_response.status_code == 405
#
#     # Test GET method
#     get_response = admin_client.get(f'{trash_url}/erase_trash_folder')
#     assert get_response.status_code == 405
#
#     # Test PUT method
#     put_response = admin_client.put(f'{trash_url}/erase_trash_folder')
#     assert put_response.status_code == 405
#
#
# def test_erase_empty_trash_folder(admin_client, admin_user):
#     """Test erasing a trash folder that is already empty."""
#     ambit_qs = admin_user.ambits.all()
#     if not ambit_qs.exists():
#         pytest.skip("Admin user has no ambits")
#     ambit = ambit_qs.first()
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#
#     # Verify trash folder is empty
#     trash_content_before = list(trash_folder.listdir())
#     assert len(trash_content_before) == 0
#
#     # Erase the empty trash folder
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#     erase_response = admin_client.delete(f'{trash_url}/erase_trash_folder')
#     assert erase_response.status_code == 200
#     response_data = erase_response.json()
#
#     # Verify response contains success_url
#     assert 'success_url' in response_data
#     assert response_data['success_url']
#
#     # Verify trash folder is still empty
#     trash_content_after = list(trash_folder.listdir())
#     assert len(trash_content_after) == 0
#
#
# def test_erase_trash_folder_sets_ambit(admin_client, admin_user, uploaded_file, sub_folder):
#     """Test that erase_trash_folder properly sets request._ambit."""
#     ambit = sub_folder.get_ambit()
#
#     # Create and delete a file
#     deletable_file = FileModel.objects.create(
#         parent=sub_folder,
#         name="test_file_for_ambit.txt",
#         file_size=uploaded_file.file_size,
#         sha1=uploaded_file.sha1,
#         owner=admin_user,
#     )
#
#     admin_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': sub_folder.id})
#     response = admin_client.post(
#         f'{admin_url}/delete',
#         json.dumps({'inode_ids': [str(deletable_file.id)]}),
#         content_type='application/json',
#     )
#     assert response.status_code == 200
#
#     # Erase the trash folder
#     trash_folder = ambit.trash_folders.get(owner=admin_user)
#     trash_url = reverse('admin:finder_inodemodel_change', kwargs={'inode_id': trash_folder.id})
#     erase_response = admin_client.delete(f'{trash_url}/erase_trash_folder')
#     assert erase_response.status_code == 200
#     response_data = erase_response.json()
#
#     # Verify the success_url contains the correct ambit slug
#     assert ambit.slug in response_data['success_url']
#
