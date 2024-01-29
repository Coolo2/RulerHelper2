
"""
PyPaginator v2.0.1 by Coolo2
"""

import discord
import typing

class PaginatorView(discord.ui.View):

    def __init__(
                self, 
                embed : discord.Embed, 
                text : str = None, 
                split_character : str = "\n", 
                per_page : int = 10, 
                index : int = 0, 
                private = None, 
                page_image_generators : typing.List[typing.Tuple[typing.Callable, tuple]] = [],
                search : bool = True,
                skip_buttons : bool = True,
                render_image_after : bool = False,
                temp_img_url : str = None
    ):
        self.embed = embed
        self.index = index or 0
        self.private : discord.User = private
        self.page_image_generators = page_image_generators
        self.attachment = None

        if not text or text == "":
            if not embed.description:
                embed.description = "_ _"
            text = (embed.description + split_character) * len(page_image_generators) if embed.description else split_character.join(["_ _"]*len(page_image_generators))
            per_page = embed.description.count(split_character)+1

        pages = text.split(split_character)
        if "" in pages:
            pages.remove("")
        
        self.pages = [split_character.join(pages[i:i+per_page]) for i in range(0, len(pages), per_page)]

        if self.index >= len(self.pages) or self.index == -1:
            self.index = len(self.pages)-1

        if len(page_image_generators) > 0 and page_image_generators[0]:
            generator = self.page_image_generators[self.index]
            
            if type(generator) == str:
                embed.set_image(url=generator)
            else:
                if not render_image_after:
                    image = generator[0](*generator[1])
                    graph = discord.File(image, filename="paginator_image.png")
                    self.attachment = graph
                    embed.set_image(url="attachment://paginator_image.png")
                else:
                    embed.set_image(url=temp_img_url)

        
        
        
        self.embed.description = self.pages[self.index] if len(pages) > 0 else "_ _"

        if self.embed.footer.text and "Page " not in self.embed.footer.text:
            self.embed.set_footer(text=f"{self.embed.footer.text} - Page {self.index+1}/{len(self.pages)}")
        else:
            self.embed.set_footer(text=f"Page {self.index+1}/{len(self.pages)}")

        super().__init__(timeout=1800)

        self.skip_buttons = skip_buttons if len(self.pages) > 2 else False

        if self.skip_buttons:
            self.children[2].disabled = self.children[3].disabled = self.index >= len(self.pages) - 1
            self.children[1].disabled = self.children[0].disabled = self.index <= 0
        else:
            self.remove_item(self.children[0])
            self.remove_item(self.children[-2])

            self.children[1].disabled = self.index >= len(self.pages) - 1
            self.children[0].disabled = self.index <= 0
        
        if not search or len(self.pages) < 2:
            self.remove_item(self.children[4 if self.skip_buttons else 2])
        
        if render_image_after:
            for child in self.children:
                child.disabled = True
    
    async def refresh(self, interaction : discord.Interaction):
        self.embed.description = self.pages[self.index]
    
        if self.skip_buttons:
            self.children[2].disabled = self.children[3].disabled = self.index >= len(self.pages) - 1
            self.children[1].disabled = self.children[0].disabled = self.index <= 0
        else:
            self.children[1].disabled = self.index >= len(self.pages) - 1
            self.children[0].disabled = self.index <= 0

        if len(self.page_image_generators)-1 >= self.index and self.page_image_generators[self.index]:
            generator = self.page_image_generators[self.index]
            
            if type(generator) == str:
                self.embed.set_image(url=generator)
            else:
                await interaction.response.defer()
                
                image = generator[0](*generator[1])
                graph = discord.File(image, filename="paginator_image.png")
                self.embed.set_image(url="attachment://paginator_image.png")

                return await interaction.followup.edit_message(embed=self.embed, view=self, attachments=[graph], message_id=interaction.message.id)
            
        await interaction.response.edit_message(embed=self.embed, view=self)
    
    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏮️", disabled=True)
    async def _left_all(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        old_index = self.index
        self.index = 0
        self.embed.set_footer(text=self.embed.footer.text.replace(f"Page {old_index+1}", f"Page {self.index+1}"))

        await self.refresh(interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="◀️", disabled=True)
    async def _left(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        self.index -= 1
        self.embed.set_footer(text=self.embed.footer.text.replace(f"Page {self.index+2}", f"Page {self.index+1}"))

        await self.refresh(interaction)

    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="▶️")
    async def _right(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        self.index += 1
        self.embed.set_footer(text=self.embed.footer.text.replace(f"Page {self.index}", f"Page {self.index+1}"))

        await self.refresh(interaction)
    
    @discord.ui.button(style=discord.ButtonStyle.secondary, emoji="⏭️", disabled=True)
    async def _right_all(self, interaction : discord.Interaction, button: discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 
        
        old_index = self.index
        self.index = len(self.pages)-1
        self.embed.set_footer(text=self.embed.footer.text.replace(f"Page {old_index+1}", f"Page {self.index+1}"))

        await self.refresh(interaction)
    
    @discord.ui.button(style=discord.ButtonStyle.primary, emoji="🔎")
    async def _search(self, interaction : discord.Interaction, button : discord.ui.Button):
        if self.private and interaction.user != self.private:
            return 

        await interaction.response.send_modal(SearchModal(self))
    
    def render_initial_image(self):
        for child in self.children:
            child.disabled = False

        generator = self.page_image_generators[self.index]
        image = generator[0](*generator[1])
        graph = discord.File(image, filename="paginator_image.png")
        self.attachment = graph
        self.embed.set_image(url="attachment://paginator_image.png")

        if self.skip_buttons:
            self.children[2].disabled = self.children[3].disabled = self.index >= len(self.pages) - 1
            self.children[1].disabled = self.children[0].disabled = self.index <= 0
        else:
            self.children[1].disabled = self.index >= len(self.pages) - 1
            self.children[0].disabled = self.index <= 0

class SearchModal(discord.ui.Modal):

    def __init__(self, paginator : PaginatorView):

        self.paginator = paginator

        super().__init__(title="Search", timeout=None)
    
    query = discord.ui.TextInput(placeholder='Enter search query here', label="Search Query", required=True, style=discord.TextStyle.short)

    async def on_submit(self, interaction : discord.Interaction):

        for i, page in enumerate(self.paginator.pages):
            
            if self.query.value.lower() in page.lower():
                embed = self.paginator.embed 

                prevIndex = self.paginator.index

                self.paginator.index = i
                embed.description = self.paginator.pages[self.paginator.index]
                embed.set_footer(text=embed.footer.text.replace(f"Page {prevIndex+1}", f"Page {i+1}"))

                return await self.paginator.refresh(interaction)
        
        return await interaction.response.send_message("Search query not found.", ephemeral=True)