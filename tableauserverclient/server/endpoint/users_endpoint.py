import copy
import logging
from typing import Optional

from tableauserverclient.server.query import QuerySet

from .endpoint import QuerysetEndpoint, api
from .exceptions import MissingRequiredFieldError, ServerResponseError
from tableauserverclient.server import RequestFactory, RequestOptions
from tableauserverclient.models import UserItem, WorkbookItem, PaginationItem, GroupItem
from ..pager import Pager

from tableauserverclient.helpers.logging import logger


class Users(QuerysetEndpoint[UserItem]):
    @property
    def baseurl(self) -> str:
        return f"{self.parent_srv.baseurl}/sites/{self.parent_srv.site_id}/users"

    # Gets all users
    @api(version="2.0")
    def get(self, req_options: Optional[RequestOptions] = None) -> tuple[list[UserItem], PaginationItem]:
        logger.info("Querying all users on site")

        if req_options is None:
            req_options = RequestOptions()
        req_options._all_fields = True

        url = self.baseurl
        server_response = self.get_request(url, req_options)
        pagination_item = PaginationItem.from_response(server_response.content, self.parent_srv.namespace)
        all_user_items = UserItem.from_response(server_response.content, self.parent_srv.namespace)
        return all_user_items, pagination_item

    # Gets 1 user by id
    @api(version="2.0")
    def get_by_id(self, user_id: str) -> UserItem:
        if not user_id:
            error = "User ID undefined."
            raise ValueError(error)
        logger.info(f"Querying single user (ID: {user_id})")
        url = f"{self.baseurl}/{user_id}"
        server_response = self.get_request(url)
        return UserItem.from_response(server_response.content, self.parent_srv.namespace).pop()

    # Update user
    @api(version="2.0")
    def update(self, user_item: UserItem, password: Optional[str] = None) -> UserItem:
        if not user_item.id:
            error = "User item missing ID."
            raise MissingRequiredFieldError(error)

        url = f"{self.baseurl}/{user_item.id}"
        update_req = RequestFactory.User.update_req(user_item, password)
        server_response = self.put_request(url, update_req)
        logger.info(f"Updated user item (ID: {user_item.id})")
        updated_item = copy.copy(user_item)
        return updated_item._parse_common_tags(server_response.content, self.parent_srv.namespace)

    # Delete 1 user by id
    @api(version="2.0")
    def remove(self, user_id: str, map_assets_to: Optional[str] = None) -> None:
        if not user_id:
            error = "User ID undefined."
            raise ValueError(error)
        url = f"{self.baseurl}/{user_id}"
        if map_assets_to is not None:
            url += f"?mapAssetsTo={map_assets_to}"
        self.delete_request(url)
        logger.info(f"Removed single user (ID: {user_id})")

    # Add new user to site
    @api(version="2.0")
    def add(self, user_item: UserItem) -> UserItem:
        url = self.baseurl
        logger.info(f"Add user {user_item.name}")
        add_req = RequestFactory.User.add_req(user_item)
        server_response = self.post_request(url, add_req)
        logger.info(server_response)
        new_user = UserItem.from_response(server_response.content, self.parent_srv.namespace).pop()
        logger.info(f"Added new user (ID: {new_user.id})")
        return new_user

    # Add new users to site. This does not actually perform a bulk action, it's syntactic sugar
    @api(version="2.0")
    def add_all(self, users: list[UserItem]):
        created = []
        failed = []
        for user in users:
            try:
                result = self.add(user)
                created.append(result)
            except Exception as e:
                failed.append(user)
        return created, failed

    # helping the user by parsing a file they could have used to add users through the UI
    # line format: Username [required], password, display name, license, admin, publish
    @api(version="2.0")
    def create_from_file(self, filepath: str) -> tuple[list[UserItem], list[tuple[UserItem, ServerResponseError]]]:
        created = []
        failed = []
        if not filepath.find("csv"):
            raise ValueError("Only csv files are accepted")

        with open(filepath) as csv_file:
            csv_file.seek(0)  # set to start of file in case it has been read earlier
            line: str = csv_file.readline()
            while line and line != "":
                user: UserItem = UserItem.CSVImport.create_user_from_line(line)
                try:
                    print(user)
                    result = self.add(user)
                    created.append(result)
                except ServerResponseError as serverError:
                    print("failed")
                    failed.append((user, serverError))
                line = csv_file.readline()
        return created, failed

    # Get workbooks for user
    @api(version="2.0")
    def populate_workbooks(self, user_item: UserItem, req_options: Optional[RequestOptions] = None) -> None:
        if not user_item.id:
            error = "User item missing ID."
            raise MissingRequiredFieldError(error)

        def wb_pager():
            return Pager(lambda options: self._get_wbs_for_user(user_item, options), req_options)

        user_item._set_workbooks(wb_pager)

    def _get_wbs_for_user(
        self, user_item: UserItem, req_options: Optional[RequestOptions] = None
    ) -> tuple[list[WorkbookItem], PaginationItem]:
        url = f"{self.baseurl}/{user_item.id}/workbooks"
        server_response = self.get_request(url, req_options)
        logger.info(f"Populated workbooks for user (ID: {user_item.id})")
        workbook_item = WorkbookItem.from_response(server_response.content, self.parent_srv.namespace)
        pagination_item = PaginationItem.from_response(server_response.content, self.parent_srv.namespace)
        return workbook_item, pagination_item

    def populate_favorites(self, user_item: UserItem) -> None:
        self.parent_srv.favorites.get(user_item)

    # Get groups for user
    @api(version="3.7")
    def populate_groups(self, user_item: UserItem, req_options: Optional[RequestOptions] = None) -> None:
        if not user_item.id:
            error = "User item missing ID."
            raise MissingRequiredFieldError(error)

        def groups_for_user_pager():
            return Pager(
                lambda options: self._get_groups_for_user(user_item, options),
                req_options,
            )

        user_item._set_groups(groups_for_user_pager)

    def _get_groups_for_user(
        self, user_item: UserItem, req_options: Optional[RequestOptions] = None
    ) -> tuple[list[GroupItem], PaginationItem]:
        url = f"{self.baseurl}/{user_item.id}/groups"
        server_response = self.get_request(url, req_options)
        logger.info(f"Populated groups for user (ID: {user_item.id})")
        group_item = GroupItem.from_response(server_response.content, self.parent_srv.namespace)
        pagination_item = PaginationItem.from_response(server_response.content, self.parent_srv.namespace)
        return group_item, pagination_item

    def filter(self, *invalid, page_size: Optional[int] = None, **kwargs) -> QuerySet[UserItem]:
        """
        Queries the Tableau Server for items using the specified filters. Page
        size can be specified to limit the number of items returned in a single
        request. If not specified, the default page size is 100. Page size can
        be an integer between 1 and 1000.

        No positional arguments are allowed. All filters must be specified as
        keyword arguments. If you use the equality operator, you can specify it
        through <field_name>=<value>. If you want to use a different operator,
        you can specify it through <field_name>__<operator>=<value>. Field
        names can either be in snake_case or camelCase.

        This endpoint supports the following fields and operators:


        domain_name=...
        domain_name__in=...
        friendly_name=...
        friendly_name__in=...
        is_local=...
        last_login=...
        last_login__gt=...
        last_login__gte=...
        last_login__lt=...
        last_login__lte=...
        luid=...
        luid__in=...
        name__cieq=...
        name=...
        name__in=...
        site_role=...
        site_role__in=...
        """

        return super().filter(*invalid, page_size=page_size, **kwargs)
